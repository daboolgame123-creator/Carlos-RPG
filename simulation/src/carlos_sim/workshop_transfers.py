"""PLAY-43/WORLD-01b: atomic, local delivery of owned inputs to a workshop.

A market purchase gives a worker a physical commodity, NOT instant workshop
stock. A qualified NPC or the player named by a signed recipe must bring their
own material to that recipe's site and deposit it as a recorded event.

No untracked inventory mutations, credit, minting or site-to-site teleport.
The existing command log and EventStore enforce idempotency and replay.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .production import MAX_BATCH, MAX_QUANTITY, _valid_name, MAX_NAME, recipe_inputs
from .market import MONEY, FORBIDDEN, _present
from .store import RevisionConflict, SQLiteEventStore
from .time_engine import TimeEngine


def deposit_workshop_material(
    state: dict[str, Any], event: DomainEvent, *, authorized: bool,
) -> None:
    """One event debits owned carried material and credits local shop stock."""
    payload = event.data
    if (not authorized or set(payload) != {"site_id", "resource", "quantity"}
            or event.actor_id is None):
        raise ValueError("workshop deposit requires a trusted worker and exact fields")
    who, site, item, amount = (
        event.actor_id, payload["site_id"], payload["resource"],
        payload["quantity"],
    )
    if (not isinstance(site, str) or site not in state["locations"]
            or not _valid_name(item, MAX_NAME)
            or item == MONEY or item in FORBIDDEN or
            type(amount) is not int or not 1 <= amount <= MAX_BATCH):
        raise ValueError("invalid workshop material, worksite or bounded quantity")
    entity = state["entities"].get(who)
    if entity is None or entity["location_id"] != site:
        raise ValueError("material depositor must be physically at the site and free")
    if entity["controller"] == "npc":
        if who not in state["npcs"] or not _present(state, who, site):
            raise ValueError("NPC material depositor must be physically present and free")
        eligible = lambda recipe: (
            "player_worker_id" not in recipe
            and recipe["role"] == state["npcs"][who]["role"]
        )
    elif entity["controller"] == "player":
        from .movement import _in_transit
        from .player_foraging import player_forage_signal
        from .player_needs import player_rest_signal
        from .production import is_producing

        player_state = WorldState.from_dict(state)
        busy_action = any(
            action["npc_id"] == who and action["status"] == "running"
            for action in state["actions"].values()
        )
        if (_in_transit(state, who) or is_producing(state, who) or busy_action
                or player_forage_signal(player_state, who) is not None
                or player_rest_signal(player_state, who) is not None):
            raise ValueError("material depositor must be physically at the site and free")
        eligible = lambda recipe: recipe.get("player_worker_id") == who
    else:
        raise ValueError("material depositor must be a player or real NPC")
    # The deposit must serve a recipe this worker can physically perform.
    if not any(
            recipe["site_id"] == site and any(
                resource == item for resource, _ in recipe_inputs(recipe))
            and eligible(recipe)
            for recipe in state["production_recipes"].values()):
        raise ValueError("not a real local production input for this worker")
    personal = state["resources"].get(who, {})
    workshop = state["resources"].get(site, {})
    owned_before, site_before = personal.get(item), workshop.get(item)
    if (type(owned_before) is not int or type(site_before) is not int
            or not 0 <= owned_before <= MAX_QUANTITY
            or not 0 <= site_before <= MAX_QUANTITY
            or owned_before < amount
            or site_before > MAX_QUANTITY - amount):
        raise ValueError("uninitialized, insufficient or overflowing physical inventory")
    # A courier's own balance may contain ONE separately consigned customer's
    # unit. Even a locally eligible worker may deposit only their OWN surplus,
    # never a third party's physically reserved cargo. Mirror consumption's
    # original cargo reservation semantics; no new ledger/authority required.
    circuit = state["supply_circuits"].get(who)
    carried = circuit["carry"] if circuit is not None else None
    reserved = int(carried is not None and carried["resource"] == item)
    if owned_before - reserved < amount:
        raise ValueError("cannot deposit a customer's reserved courier cargo")
    # Complete atomic double-entry commodity transfer, no monetary mutation.
    personal[item] = owned_before - amount
    workshop[item] = site_before + amount


@dataclass(frozen=True)
class WorkshopDepositResult:
    state: WorldState
    site_id: str
    resource: str
    deposited_quantity: int


class NPCWorkshopService:
    """Trusted NPC-only workshop deposit, not a public unguarded inventory API."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("workshop service must share the same event store")
        self.store, self.clock = store, clock

    def deposit(
        self, world_id: str, npc_id: str, site_id: str, resource: str,
        quantity: int, *, command_id: str, expected_revision: int,
    ) -> WorkshopDepositResult:
        self.clock._require_session(world_id)
        current = self.store.load(world_id)
        if current.revision != expected_revision:
            raise RevisionConflict("stale workshop deposit revision")
        if npc_id not in current.npcs:
            raise PermissionError("only a real NPC may deposit workshop stock")
        if not isinstance(command_id, str) or not command_id:
            raise ValueError("deposit command requires a unique nonempty ID")
        event = DomainEvent(
            "WorkshopMaterialDeposited", npc_id,
            "owner delivers personally carried inputs into local workshop",
            current.time,
            {"site_id": site_id, "resource": resource, "quantity": quantity},
        )
        result = self.store.append(
            world_id, "workshop-deposit:" + command_id,
            expected_revision, [event],
            production_authorized=True, market_authorized=True,
        )
        return WorkshopDepositResult(result, site_id, resource, quantity)
