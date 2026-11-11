"""SQLite transactional event store with verified snapshots and idempotent commands."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Sequence
from collections.abc import Mapping
from .domain import WorldState, DomainEvent, apply_event, canonical, canonical_hash, SCHEMA_VERSION, RULES_VERSION

class RevisionConflict(Exception): pass
class InvalidEvent(Exception): pass
class IntegrityError(Exception): pass
class UnsupportedVersion(Exception): pass
class DuplicateCommand(Exception): pass

class SQLiteEventStore:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self._active_worlds: set[str] = set()
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS worlds (
                id TEXT PRIMARY KEY, revision INTEGER NOT NULL, sim_time INTEGER NOT NULL,
                schema_version INTEGER NOT NULL, rules_version INTEGER NOT NULL,
                initial_state TEXT NOT NULL, initial_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS commands (
                world_id TEXT NOT NULL REFERENCES worlds(id), command_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, first_revision INTEGER NOT NULL,
                last_revision INTEGER NOT NULL, bootstrap INTEGER NOT NULL DEFAULT 0,
                clock_authorized INTEGER NOT NULL DEFAULT 0,
                npc_authorized INTEGER NOT NULL DEFAULT 0,
                action_authorized INTEGER NOT NULL DEFAULT 0,
                movement_authorized INTEGER NOT NULL DEFAULT 0,
                social_authorized INTEGER NOT NULL DEFAULT 0,
                assistance_authorized INTEGER NOT NULL DEFAULT 0,
                consumption_authorized INTEGER NOT NULL DEFAULT 0,
                survival_authorized INTEGER NOT NULL DEFAULT 0,
                rpg_authorized INTEGER NOT NULL DEFAULT 0,
                production_authorized INTEGER NOT NULL DEFAULT 0,
                market_authorized INTEGER NOT NULL DEFAULT 0,
                loan_authorized INTEGER NOT NULL DEFAULT 0,
                taking_authorized INTEGER NOT NULL DEFAULT 0,
                claim_authorized INTEGER NOT NULL DEFAULT 0,
                complaint_authorized INTEGER NOT NULL DEFAULT 0,
                permission_authorized INTEGER NOT NULL DEFAULT 0,
                claim_transfer_authorized INTEGER NOT NULL DEFAULT 0,
                injury_authorized INTEGER NOT NULL DEFAULT 0,
                recovery_authorized INTEGER NOT NULL DEFAULT 0,
                gift_authorized INTEGER NOT NULL DEFAULT 0,
                agriculture_authorized INTEGER NOT NULL DEFAULT 0,
                supply_authorized INTEGER NOT NULL DEFAULT 0,
                hydrology_authorized INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(world_id, command_id));
            CREATE TABLE IF NOT EXISTS events (
                world_id TEXT NOT NULL REFERENCES worlds(id), seq INTEGER NOT NULL,
                command_id TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
                PRIMARY KEY(world_id,seq), FOREIGN KEY(world_id,command_id)
                    REFERENCES commands(world_id,command_id));
            CREATE TABLE IF NOT EXISTS snapshots (
                world_id TEXT NOT NULL REFERENCES worlds(id), revision INTEGER NOT NULL,
                state TEXT NOT NULL, hash TEXT NOT NULL,
                PRIMARY KEY(world_id,revision));
        """)

    def close(self) -> None:
        self._active_worlds.clear()
        self.db.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def create_world(self, world_id: str) -> WorldState:
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world ID required")
        state = WorldState(world_id)
        d = state.to_dict()
        payload = canonical(d)
        with self.db:
            self.db.execute("INSERT INTO worlds VALUES(?,?,?,?,?,?,?)", (world_id, 0, 0, SCHEMA_VERSION, RULES_VERSION, payload, canonical_hash(d)))
        return state

    def _world_row(self, world_id: str):
        row = self.db.execute("SELECT revision,sim_time,schema_version,rules_version,initial_state,initial_hash FROM worlds WHERE id=?", (world_id,)).fetchone()
        if row is None: raise KeyError(world_id)
        if row[2] != SCHEMA_VERSION or row[3] != RULES_VERSION: raise UnsupportedVersion("world schema/rules mismatch")
        return row

    def _decode_state(self, payload: str, expected_hash: str) -> WorldState:
        try:
            d = json.loads(payload)
            if canonical_hash(d) != expected_hash:
                raise IntegrityError("state hash mismatch")
            return WorldState.from_dict(d)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise IntegrityError("invalid stored state") from exc

    def load(self, world_id: str, *, use_snapshot: bool = True) -> WorldState:
        row = self._world_row(world_id)
        state = self._decode_state(row[4], row[5])
        if state.world_id != world_id or state.revision != 0:
            raise IntegrityError("invalid initial state")
        if use_snapshot:
            snap = self.db.execute("SELECT revision,state,hash FROM snapshots WHERE world_id=? ORDER BY revision DESC LIMIT 1",(world_id,)).fetchone()
            if snap:
                state = self._decode_state(snap[1], snap[2])
                if state.world_id != world_id or state.revision != snap[0] or state.revision > row[0]:
                    raise IntegrityError("snapshot identity/revision mismatch")
        # Join capability provenance once for the replay stream rather than
        # issuing an additional command lookup for every individual event.
        # LEFT JOIN is deliberate: a damaged/missing command must still fail
        # integrity verification instead of silently dropping its events.
        replay_query = (
            "SELECT e.seq, e.payload, e.hash, c.request_hash, c.bootstrap, "
            "c.action_authorized, c.movement_authorized, c.social_authorized, "
            "c.assistance_authorized, c.consumption_authorized, c.survival_authorized, c.rpg_authorized, c.production_authorized, c.market_authorized, c.loan_authorized, c.taking_authorized, c.claim_authorized, c.complaint_authorized, c.permission_authorized, c.claim_transfer_authorized, c.injury_authorized, c.recovery_authorized, c.gift_authorized, c.agriculture_authorized, c.supply_authorized, c.hydrology_authorized "
            "FROM events AS e LEFT JOIN commands AS c "
            "ON e.world_id=c.world_id AND e.command_id=c.command_id "
            "WHERE e.world_id=? AND e.seq>? ORDER BY e.seq"
        )
        for (seq, raw, stored_hash, command_hash, bootstrap,
             action_authorized, movement_authorized, social_authorized,
             assistance_authorized, consumption_authorized,
             survival_authorized, rpg_authorized, production_authorized, market_authorized, loan_authorized, taking_authorized, claim_authorized, complaint_authorized, permission_authorized, claim_transfer_authorized, injury_authorized, recovery_authorized, gift_authorized, agriculture_authorized, supply_authorized, hydrology_authorized) in self.db.execute(
                 replay_query, (world_id, state.revision)):
            if seq != state.revision + 1:
                raise IntegrityError("event sequence gap")
            try:
                raw_data = json.loads(raw)
                if canonical_hash(raw_data) != stored_hash:
                    raise IntegrityError("event hash mismatch")
                if command_hash is None:
                    raise IntegrityError("event command is missing")
                state = apply_event(
                    state, DomainEvent.from_dict(raw_data),
                    bootstrap=bool(bootstrap),
                    action_authorized=bool(action_authorized),
                    movement_authorized=bool(movement_authorized),
                    social_authorized=bool(social_authorized),
                    assistance_authorized=bool(assistance_authorized),
                    consumption_authorized=bool(consumption_authorized),
                    survival_authorized=bool(survival_authorized),
                    rpg_authorized=bool(rpg_authorized),
                    production_authorized=bool(production_authorized),
                    market_authorized=bool(market_authorized),
                    loan_authorized=bool(loan_authorized),
                    taking_authorized=bool(taking_authorized),
                    claim_authorized=bool(claim_authorized),
                    complaint_authorized=bool(complaint_authorized),
                    permission_authorized=bool(permission_authorized),
                    claim_transfer_authorized=bool(claim_transfer_authorized),
                    injury_authorized=bool(injury_authorized),
                    recovery_authorized=bool(recovery_authorized),
                    gift_authorized=bool(gift_authorized),
                    agriculture_authorized=bool(agriculture_authorized),
                    supply_authorized=bool(supply_authorized),
                    hydrology_authorized=bool(hydrology_authorized),
                )
            except (ValueError, TypeError) as exc:
                raise IntegrityError(f"corrupt event {seq}") from exc
        if state.revision != row[0] or state.time != row[1]:
            raise IntegrityError("world head mismatch")
        from .actions import validate_action_reservations
        try:
            validate_action_reservations(state)
        except ValueError as exc:
            raise IntegrityError(str(exc)) from exc
        from .movement import validate_travel_reservations
        try:
            validate_travel_reservations(state)
        except ValueError as exc:
            raise IntegrityError(str(exc)) from exc
        from .recovery_events import validate_treatment_reservations
        try:
            validate_treatment_reservations(state)
        except ValueError as exc:
            raise IntegrityError(str(exc)) from exc
        return state

    def append(self, world_id: str, command_id: str, expected_revision: int, events: Sequence[DomainEvent], *, bootstrap: bool = False, clock_authorized: bool = False, npc_authorized: bool = False, action_authorized: bool = False, movement_authorized: bool = False, social_authorized: bool = False, assistance_authorized: bool = False, consumption_authorized: bool = False, survival_authorized: bool = False, rpg_authorized: bool = False, production_authorized: bool = False, market_authorized: bool = False, loan_authorized: bool = False, taking_authorized: bool = False, claim_authorized: bool = False, complaint_authorized: bool = False, permission_authorized: bool = False, claim_transfer_authorized: bool = False, injury_authorized: bool = False, recovery_authorized: bool = False, gift_authorized: bool = False, agriculture_authorized: bool = False, supply_authorized: bool = False, hydrology_authorized: bool = False) -> WorldState:
        """Commit events atomically. bootstrap is a trusted setup-only capability.

        Never expose this method or its bootstrap switch to untrusted callers.
        A future application authorization layer must guard the capability.
        """
        if not isinstance(command_id,str) or not command_id or type(expected_revision) is not int or expected_revision < 0 or not events:
            raise ValueError("command ID, expected revision and nonempty event batch required")
        if type(bootstrap) is not bool or type(clock_authorized) is not bool or type(npc_authorized) is not bool or type(action_authorized) is not bool or type(movement_authorized) is not bool or type(social_authorized) is not bool or type(assistance_authorized) is not bool or type(consumption_authorized) is not bool or type(survival_authorized) is not bool or type(rpg_authorized) is not bool or type(production_authorized) is not bool or type(market_authorized) is not bool or type(loan_authorized) is not bool or type(taking_authorized) is not bool or type(claim_authorized) is not bool or type(complaint_authorized) is not bool or type(permission_authorized) is not bool or type(claim_transfer_authorized) is not bool or type(injury_authorized) is not bool or type(recovery_authorized) is not bool or type(gift_authorized) is not bool or type(agriculture_authorized) is not bool or type(supply_authorized) is not bool or type(hydrology_authorized) is not bool:
            raise ValueError("capability flags must be boolean")
        if (any(e.event_type == "RecoveryStarted" for e in events)
                or any(e.event_type == "ScheduledEventCreated" and "__npc_recovery" in e.data.get("payload", {}) for e in events)):
            if not recovery_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("recovery requires active session and separate capability")
        if any(e.event_type == "InjuryRecorded" for e in events) and not bootstrap:
            if not injury_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("runtime injury requires active session and dedicated capability")
        if any(e.event_type in {"RegisteredClaimTransferOffered", "RegisteredClaimTransferAccepted", "RegisteredClaimTransferCancelled"} for e in events):
            if not claim_transfer_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("historical claim assignments require independent local capability and active session")
        if any(e.event_type in {"PropertyPermissionGranted", "PropertyPermissionRevoked"} for e in events):
            if not permission_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("rights permissions require trusted local capability and active session")
        if any(e.event_type in {"PropertyComplaintReceived", "PropertyComplaintAcknowledged"} for e in events):
            if not complaint_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("complaints require trusted local capability and active session")
        if any(e.event_type == "PropertyClaimFiled" for e in events):
            if not claim_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("property claim requires active session and independent claim capability")
        if any(e.event_type == "PropertyTaken" for e in events):
            if not taking_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("taking requires active session and independent property capability")
        if any(e.event_type in {"LoanProposed", "LoanClosed", "LoanAccepted", "LoanRepaid"} for e in events):
            if not loan_authorized:
                raise InvalidEvent("loan agreements require trusted loan capability")
            if world_id not in self._active_worlds:
                raise InvalidEvent("loan agreements require active play session")
        # PLAY-17 activity memory is exclusively an explicit human look.
        # The reducer also revalidates every reported local activity against
        # real physical actions at that event's own logical time. Do not
        # accept fabricated memory attached to a clock, foraging or NPC command.
        if any(e.event_type == "PlayerObserved" and "activities" in e.data
               for e in events):
            if (not movement_authorized or not command_id.startswith("player-observe:")
                    or len(events) != 1 or events[0].event_type != "PlayerObserved"
                    or events[0].cause != "player deliberately looked around locally"
                    or world_id not in self._active_worlds):
                raise InvalidEvent("historical activity evidence requires a dedicated active look")
        for idx, event in enumerate(events):
            payload = event.data.get("payload", {})
            if (event.event_type != "ScheduledEventCreated"
                    or not isinstance(payload, Mapping)
                    or "__player_forage" not in payload):
                continue
            if not action_authorized or not movement_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("timed forage requires trusted active action and local observation")
            if idx == 0:
                raise InvalidEvent("timed forage requires immediately preceding player observation")
            sight = events[idx - 1]
            fields = payload["__player_forage"]
            if (not isinstance(fields, Mapping)
                    or sight.event_type != "PlayerObserved"
                    or sight.actor_id != fields.get("player_id")
                    or sight.time != event.time
                    or sight.data.get("location_id") != fields.get("site_id")):
                raise InvalidEvent("timed forage requires matching same-command local observation")
        if any(e.event_type == "PlayerFoodCollected" for e in events):
            if not action_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("player food collection requires a trusted action capability and active session")
            for idx, event in enumerate(events):
                if event.event_type != "PlayerFoodCollected":
                    continue
                if idx == 0:
                    raise InvalidEvent("food pickup requires an immediately preceding local observation")
                sight = events[idx - 1]
                if (sight.event_type != "PlayerObserved"
                        or sight.actor_id != event.actor_id
                        or sight.time != event.time
                        or sight.data.get("location_id") != event.data.get("site_id")
                        or not movement_authorized):
                    raise InvalidEvent("food pickup requires a matching trusted local observation")
        if any(e.event_type == "PlayerFoodEaten" for e in events):
            if not consumption_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("player eating requires trusted consumption capability and active session")
        # PLAY-32 quests are player-originated RPG commands, never autonomous
        # NPC/admin mutations or fabricated reward events.
        if any(e.event_type in ("PlayerQuestAccepted", "PlayerQuestRewardClaimed")
               for e in events):
            if (not rpg_authorized or world_id not in self._active_worlds
                    or not command_id.startswith("player-quest:")
                    or len(events) != 1):
                raise InvalidEvent("quest changes require one explicit trusted player command")
        if any(e.event_type == "PlayerGiftDelivered" for e in events):
            if not gift_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("player gift requires dedicated capability and active session")
        if any(e.event_type in {"MarketOfferPosted", "MarketTradeExecuted", "MarketOfferClosed"} for e in events):
            if not market_authorized:
                raise InvalidEvent("market transactions require trusted market capability")
            if world_id not in self._active_worlds:
                raise InvalidEvent("market transactions require active play session")
        if any(e.event_type == "RainWaterRecorded" for e in events):
            if not hydrology_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("rain needs active dedicated hydrology authority")
        # A newly produced MARKET loaf can re-fund an EXISTING signed
        # food wage only after an immediately preceding, verified physical
        # food delivery in this exact, authorized, active supply command.
        # This extension never grants the right to create a new contract.
        if any(e.event_type == "CourierProvisionReplenished" for e in events):
            if bootstrap or not supply_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("market food re-funding requires trusted active supply")
            for i, refill in enumerate(events):
                if refill.event_type != "CourierProvisionReplenished":
                    continue
                if i == 0:
                    raise InvalidEvent("food wage refill requires earlier actual delivery")
                delivered = events[i-1]
                if (delivered.event_type != "SupplyCargoDelivered"
                        or delivered.actor_id != refill.data.get("courier_id")
                        or delivered.data.get("courier_id") != refill.data.get("courier_id")
                        or delivered.data.get("resource") != "food"
                        or delivered.time != refill.time):
                    raise InvalidEvent("food wage refill must immediately follow real market food delivery")
        # A physically delivered bakery loaf may be escrowed by its FARM
        # owner only immediately after the corresponding authentic return.
        # It is not a wage yet: a future water delivery must be proven again.
        if any(e.event_type == "CourierFarmProvisionReplenished" for e in events):
            if bootstrap or not supply_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("farm bread escrow requires trusted active supply")
            for i, fund in enumerate(events):
                if fund.event_type != "CourierFarmProvisionReplenished":
                    continue
                if i == 0:
                    raise InvalidEvent("farm escrow requires immediately preceding food arrival")
                arrived = events[i - 1]
                if (arrived.event_type != "SupplyCargoDelivered"
                        or arrived.actor_id != fund.data.get("courier_id")
                        or arrived.data.get("courier_id") != fund.data.get("courier_id")
                        or arrived.data.get("resource") != "food"
                        or arrived.time != fund.time):
                    raise InvalidEvent("farm escrow must follow actual same-courier bread delivery")
        if any(e.event_type == "CourierProvisionPaid" for e in events):
            if bootstrap or not supply_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("food wage requires active trusted supply service")
            for i, wage in enumerate(events):
                if wage.event_type != "CourierProvisionPaid":
                    continue
                # H1 default: preserve the original strict immediately
                # preceding FOOD delivery evidence byte-for-byte.
                # H3 explicit opt-in: a prior authenticated physical
                # water/grain/food receipt in THIS SAME atomic command
                # also proves completed work, with payment at market checked
                # by the state reducer. Never trust a caller's counter alone.
                if wage.data.get("proof") == "farm_water_delivery":
                    # A farm can pay a ration only when its courier really
                    # dropped off WATER here, after physically walking the
                    # well→field road in this very trusted atomic command.
                    if i == 0:
                        raise InvalidEvent("farm courier wage needs real water delivered")
                    source = events[i-1]
                    if (source.event_type != "SupplyCargoDelivered"
                            or source.actor_id != wage.data.get("courier_id")
                            or source.data.get("courier_id") != wage.data.get("courier_id")
                            or source.data.get("resource") != "water"
                            or source.time != wage.time):
                        raise InvalidEvent("farm courier wage requires immediate authentic water delivery")
                elif wage.data.get("proof") == "bakery_grain_delivery":
                    # This distinct site-owned bakery wage is earned ONLY
                    # immediately after the same courier has physically
                    # delivered authentic GRAIN to that same bakery stop.
                    # The reducer further verifies site, route index, escrow,
                    # unique receipt and presence; no old-market shortcut.
                    if i == 0:
                        raise InvalidEvent("bakery wage requires same-command grain delivery")
                    source = events[i-1]
                    if (source.event_type != "SupplyCargoDelivered"
                            or source.actor_id != wage.data.get("courier_id")
                            or source.data.get("courier_id") != wage.data.get("courier_id")
                            or source.data.get("resource") != "grain"
                            or source.time != wage.time):
                        raise InvalidEvent("bakery wage requires immediate real grain delivery")
                elif wage.data.get("proof") == "prior_market_service":
                    witnessed = any(
                        source.event_type == "SupplyCargoDelivered"
                        and source.actor_id == wage.data.get("courier_id")
                        and source.data.get("courier_id") == wage.data.get("courier_id")
                        and source.data.get("resource") in ("water", "grain", "food")
                        and source.time <= wage.time
                        for source in events[:i]
                    )
                    if not witnessed:
                        raise InvalidEvent("early courier food wage needs an earlier same-command physical delivery")
                else:
                    if i == 0:
                        raise InvalidEvent("food wage requires same-command delivery receipt")
                    source = events[i-1]
                    if source.event_type == "CourierProvisionReplenished":
                        # One legal alternative to the strict H1 adjacency:
                        # verified DELIVERY -> site-OWNED refill -> PAY,
                        # all three adjacent in this one SQLite command.
                        if (i < 2 or source.time != wage.time
                                or source.data.get("id") != wage.data.get("id")
                                or source.data.get("courier_id") != wage.data.get("courier_id")
                                or source.data.get("service_deliveries")
                                    != wage.data.get("service_deliveries")):
                            raise InvalidEvent("re-funded food wage does not match proven service")
                        source = events[i-2]
                    if (source.event_type != "SupplyCargoDelivered"
                            or source.actor_id != wage.data.get("courier_id")
                            or source.data.get("courier_id") != wage.data.get("courier_id")
                            or source.data.get("resource") != "food"
                            or source.time != wage.time):
                        raise InvalidEvent("food wage must immediately follow its physical market delivery")
        if any(e.event_type in ("SupplyCargoPicked", "SupplyCargoDelivered") for e in events):
            if not supply_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("cargo needs active trusted physical supply capability")
        if any(e.event_type == "CropGrowthStarted" for e in events):
            if not agriculture_authorized or world_id not in self._active_worlds:
                raise InvalidEvent("crop growth needs protected active agriculture capability")
        if any(e.event_type in ("ProductionStarted", "ProductionWagePaid") for e in events):
            if not production_authorized or bootstrap:
                raise InvalidEvent("production and wages need trusted runtime capability")
            if world_id not in self._active_worlds:
                raise InvalidEvent("production and wages require active play session")
        if any(e.event_type == "WorkshopMaterialDeposited" for e in events):
            if (bootstrap or not production_authorized or not market_authorized
                    or world_id not in self._active_worlds):
                raise InvalidEvent(
                    "workshop deposit needs active trusted production and market capabilities"
                )
        if any(e.event_type == 'PlayerVitalChanged' for e in events):
            if not rpg_authorized:
                raise InvalidEvent('RPG vital changes require trusted RPG capability')
            if world_id not in self._active_worlds:
                raise InvalidEvent('RPG vital changes require active play session')
        if survival_authorized and not clock_authorized:
            raise InvalidEvent("survival progress requires trusted clock capability")
        if any(e.event_type in ("TimeAdvanced", "ScheduledEventFired") for e in events):
            if not clock_authorized:
                raise InvalidEvent("clock advancement/firing requires a trusted clock capability")
            if world_id not in self._active_worlds:
                raise InvalidEvent("clock cannot advance outside an active play session")
        if any(e.event_type == "NPCDecisionRecorded" and e.data.get("action") == "forage"
               for e in events) and not action_authorized:
            raise InvalidEvent("foraging decisions require trusted action capability")
        if not npc_authorized and any(e.event_type == "NPCDecisionRecorded" for e in events):
            raise InvalidEvent("NPC decisions require a trusted planner capability")
        npc_mutations = {"NPCInformationDelivered", "NPCBeliefReceived", "NPCNeedChanged", "NPCDecisionRecorded"}
        if any(e.event_type in npc_mutations for e in events) and world_id not in self._active_worlds:
            raise InvalidEvent("NPC state cannot change outside an active play session")
        if any(e.event_type == "NPCInformationDelivered" for e in events) and not npc_authorized:
            raise InvalidEvent("information delivery requires a trusted NPC capability")
        if any(e.event_type == "NPCActionStarted" for e in events) and not action_authorized:
            raise InvalidEvent("NPC action start requires trusted action capability")
        if any(e.event_type == "NPCActionStarted" for e in events) and world_id not in self._active_worlds:
            raise InvalidEvent("NPC actions cannot start outside an active play session")
        movement_events = {"NPCTravelStarted", "NPCObserved", "PlayerObserved", "NPCNavigationSurveyed", "NPCNavigationTargetSet"}
        if any(e.event_type in movement_events
               or (e.event_type == "ScheduledEventCreated"
                   and "__player_travel" in e.data.get("payload", {}))
               for e in events):
            if not movement_authorized:
                raise InvalidEvent("NPC travel/perception requires trusted movement capability")
            if world_id not in self._active_worlds:
                raise InvalidEvent("NPC travel/perception requires active play session")
        if any(e.event_type == 'RumorDelivered' for e in events):
            if not social_authorized:
                raise InvalidEvent('rumor delivery requires trusted social capability')
            if world_id not in self._active_worlds:
                raise InvalidEvent('rumor delivery requires active play session')
        if any(e.event_type in ('SocialMessageSent', 'SocialMessageReceived', 'PlayerHearsayReceived') for e in events):
            if not social_authorized:
                raise InvalidEvent('social interaction requires trusted local capability')
            if world_id not in self._active_worlds:
                raise InvalidEvent('social interaction requires active play session')
        assistance_events = {'AssistanceRequested', 'AssistanceResponded', 'AssistanceFulfilled', 'AssistanceCancelled'}
        if any(e.event_type in assistance_events for e in events):
            if not assistance_authorized:
                raise InvalidEvent('resource-backed assistance requires trusted assistance capability')
            if world_id not in self._active_worlds:
                raise InvalidEvent('assistance requires an active play session')
        # A generic NPCNeedChanged event remains useful for scenario setup,
        # illness and other trusted interventions. However, lowering hunger
        # without consuming food must not be accessible through the ordinary
        # NPC event path: that would bypass the new meal/inventory ledger.
        # The existing npc_authorized capability explicitly marks such an
        # administrative adjustment (and is recorded for deterministic replay).
        if any(e.event_type == "NPCNeedChanged"
               and e.data.get("need") == "hunger"
               and type(e.data.get("previous")) is int
               and type(e.data.get("current")) is int
               and e.data["current"] < e.data["previous"]
               for e in events) and not npc_authorized:
            raise InvalidEvent("lowering hunger outside eating requires trusted NPC adjustment capability")
        if any(e.event_type == "NPCFoodGathered" for e in events):
            if not action_authorized:
                raise InvalidEvent("food gathering requires trusted action capability")
            if world_id not in self._active_worlds:
                raise InvalidEvent("NPC cannot gather food outside an active play session")
        if any(e.event_type == "NPCFoodConsumed" for e in events):
            if not consumption_authorized:
                raise InvalidEvent("eating requires trusted consumption capability")
            if world_id not in self._active_worlds:
                raise InvalidEvent("NPC cannot eat outside an active play session")
        # Gameplay consumption is a state mutation, not a background administrative
        # update. Initial inventory setup remains permitted only at bootstrap.
        if any(e.event_type == "ResourceChanged" and e.data.get("source") != "initialization"
               for e in events) and world_id not in self._active_worlds:
            raise InvalidEvent("resource consumption requires an active play session")
        # First-hand activity and care evidence must follow the observer's
        # own NPCObserved event in this SAME atomic command. A same-tick
        # earlier look cannot be retroactively upgraded into new evidence.
        for i, evidence in enumerate(events):
            if (evidence.event_type == "NPCInformationDelivered"
                    and isinstance(evidence.data.get("key"), str)
                    and evidence.data["key"].startswith(("visible-care:", "visible-rest:"))):
                who = evidence.data.get("npc_id")
                sights = [j for j, previous in enumerate(events[:i])
                          if previous.event_type == "NPCObserved"
                          and previous.actor_id == who
                          and previous.data.get("npc_id") == who]
                if not movement_authorized or not npc_authorized or not sights:
                    raise InvalidEvent("first-hand activity requires same-command observation")
                if (evidence.data["key"].startswith("visible-care:")
                        and any(previous.event_type == "RecoveryStarted"
                                for previous in events[sights[-1] + 1:i])):
                    raise InvalidEvent("care must start before the witnessed observation")
        serialized = [e.to_dict() for e in events]
        request_hash = canonical_hash({"events":serialized,"expected_revision":expected_revision,"bootstrap":bootstrap,"clock_authorized":clock_authorized,"npc_authorized":npc_authorized,"action_authorized":action_authorized,"movement_authorized":movement_authorized,"social_authorized":social_authorized,"assistance_authorized":assistance_authorized,"consumption_authorized":consumption_authorized,"survival_authorized":survival_authorized,"rpg_authorized":rpg_authorized,"production_authorized":production_authorized,"market_authorized":market_authorized,"loan_authorized":loan_authorized,"taking_authorized":taking_authorized,"claim_authorized":claim_authorized,"complaint_authorized":complaint_authorized,"permission_authorized":permission_authorized,"claim_transfer_authorized":claim_transfer_authorized,"injury_authorized":injury_authorized,"recovery_authorized":recovery_authorized,"gift_authorized":gift_authorized,"agriculture_authorized":agriculture_authorized,"supply_authorized":supply_authorized,"hydrology_authorized":hydrology_authorized})
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT request_hash FROM commands WHERE world_id=? AND command_id=?",(world_id,command_id)).fetchone()
            if existing:
                if existing[0] == request_hash:
                    self.db.execute("COMMIT")
                    return self.load(world_id)
                raise DuplicateCommand("command ID was already used with different data")
            state = self.load(world_id)
            if state.revision != expected_revision:
                raise RevisionConflict(f"expected {expected_revision}, current {state.revision}")
            first = state.revision + 1
            for e in events:
                try:
                    state = apply_event(state,e,bootstrap=bootstrap,action_authorized=action_authorized,movement_authorized=movement_authorized,social_authorized=social_authorized,assistance_authorized=assistance_authorized,consumption_authorized=consumption_authorized,survival_authorized=survival_authorized,rpg_authorized=rpg_authorized,production_authorized=production_authorized,market_authorized=market_authorized,loan_authorized=loan_authorized,taking_authorized=taking_authorized,claim_authorized=claim_authorized,complaint_authorized=complaint_authorized,permission_authorized=permission_authorized,claim_transfer_authorized=claim_transfer_authorized,injury_authorized=injury_authorized,recovery_authorized=recovery_authorized,gift_authorized=gift_authorized,agriculture_authorized=agriculture_authorized,supply_authorized=supply_authorized,hydrology_authorized=hydrology_authorized)
                except (ValueError,TypeError) as exc:
                    raise InvalidEvent(str(exc)) from exc
            from .actions import validate_action_reservations
            try:
                validate_action_reservations(state)
            except ValueError as exc:
                raise InvalidEvent(str(exc)) from exc
            from .movement import validate_travel_reservations
            try:
                validate_travel_reservations(state)
            except ValueError as exc:
                raise InvalidEvent(str(exc)) from exc
            from .recovery_events import validate_treatment_reservations
            try:
                validate_treatment_reservations(state)
            except ValueError as exc:
                raise InvalidEvent(str(exc)) from exc
            self.db.execute("INSERT INTO commands VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(world_id,command_id,request_hash,first,state.revision,int(bootstrap),int(clock_authorized),int(npc_authorized),int(action_authorized),int(movement_authorized),int(social_authorized),int(assistance_authorized),int(consumption_authorized),int(survival_authorized),int(rpg_authorized),int(production_authorized),int(market_authorized),int(loan_authorized),int(taking_authorized),int(claim_authorized),int(complaint_authorized),int(permission_authorized),int(claim_transfer_authorized),int(injury_authorized),int(recovery_authorized),int(gift_authorized),int(agriculture_authorized),int(supply_authorized),int(hydrology_authorized)))
            for idx, data in enumerate(serialized,start=first):
                self.db.execute("INSERT INTO events VALUES(?,?,?,?,?)",(world_id,idx,command_id,canonical(data),canonical_hash(data)))
            self.db.execute("UPDATE worlds SET revision=?,sim_time=? WHERE id=? AND revision=?",(state.revision,state.time,world_id,expected_revision))
            if self.db.execute("SELECT changes()").fetchone()[0] != 1:
                raise RevisionConflict("concurrent update")
            self.db.execute("COMMIT")
            return state
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def snapshot(self, world_id: str) -> WorldState:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            state = self.load(world_id)
            d = state.to_dict()
            self.db.execute("INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?)", (world_id,state.revision,canonical(d),canonical_hash(d)))
            self.db.execute("COMMIT")
            return state
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def verify(self, world_id: str) -> WorldState:
        """Rebuild from genesis and compare to the latest snapshot-based projection."""
        full = self.load(world_id,use_snapshot=False)
        quick = self.load(world_id)
        if canonical_hash(full.to_dict()) != canonical_hash(quick.to_dict()):
            raise IntegrityError("snapshot and full replay disagree")
        return full

    def player_view(self, world_id: str) -> dict:
        """Safe-by-default: do not publish entities, resources or hidden state.

        Dedicated perception/visibility logic is deferred to a later phase.
        """
        state = self.load(world_id)
        return {"world_id": state.world_id, "time": state.time, "revision":state.revision}
