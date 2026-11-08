"""PLAY-32: one bounded, evidence-backed player quest and a funded reward.

Quest progress derives exclusively from a verified MarketTradeExecuted reducer.
Claiming moves existing copper from the market's credited sales ledger. This
introduces no currency, items, levels or fabricated player/NPC knowledge.
All quest events require an explicit trusted player command and active session.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent
from .market import MAX_AMOUNT, _balance, _present
from .movement import _in_transit

QUEST_ID = "market_first_loaf"
REWARD_OWNER = "market"
REWARD_RESOURCE = "coin_copper"
REWARD_AMOUNT = 1
QUEST_TITLE = "First market loaf"


def _qualifying_trade(trade: Any, player_id: str) -> bool:
    return (
        isinstance(trade, dict)
        and trade.get("buyer_id") == player_id
        and trade.get("site_id") == "market"
        and trade.get("seller_id") == "salma"
        and trade.get("stock_owner_id") == REWARD_OWNER
        and trade.get("resource") == "food"
        and trade.get("payment_resource") == REWARD_RESOURCE
        and type(trade.get("unit_price")) is int
        and trade["unit_price"] >= 2
        and type(trade.get("quantity")) is int
        and trade["quantity"] >= 1
    )


def validate_player_quests(state: dict[str, Any]) -> None:
    for player, owned in state["player_quests"].items():
        if (player not in state["entities"]
                or state["entities"][player]["controller"] != "player"
                or not isinstance(owned, dict)
                or set(owned) != {QUEST_ID}):
            raise ValueError("invalid quest ownership")
        q = owned[QUEST_ID]
        if not isinstance(q, dict) or set(q) != {
            "accepted_at", "completed_at", "evidence_trade_id",
            "claimed_at", "reward_from_before", "reward_from_after",
            "reward_to_before", "reward_to_after",
        }:
            raise ValueError("invalid quest record")
        accepted, done, trade_id, claimed = (
            q["accepted_at"], q["completed_at"],
            q["evidence_trade_id"], q["claimed_at"]
        )
        if type(accepted) is not int or not 0 <= accepted <= state["time"]:
            raise ValueError("invalid quest acceptance")
        if done is None:
            if trade_id is not None or claimed is not None:
                raise ValueError("unearned quest progress")
        else:
            if (type(done) is not int or not accepted <= done <= state["time"]
                    or not isinstance(trade_id, str)
                    or trade_id not in state["market_trades"]
                    or not _qualifying_trade(state["market_trades"][trade_id], player)
                    or state["market_trades"][trade_id]["executed_at"] != done):
                raise ValueError("quest completion without real market receipt")
        reward_fields = ("reward_from_before", "reward_from_after",
                         "reward_to_before", "reward_to_after")
        if claimed is None:
            if any(q[k] is not None for k in reward_fields):
                raise ValueError("unclaimed quest cannot contain a payout")
        else:
            if (done is None or type(claimed) is not int
                    or not done <= claimed <= state["time"]
                    or any(type(q[k]) is not int for k in reward_fields)
                    or q["reward_from_before"] < REWARD_AMOUNT
                    or q["reward_from_after"] != q["reward_from_before"] - REWARD_AMOUNT
                    or q["reward_to_before"] < 0
                    or q["reward_to_after"] != q["reward_to_before"] + REWARD_AMOUNT
                    or q["reward_to_after"] > MAX_AMOUNT):
                raise ValueError("quest payout lacks finite physical funding")


def _available(state: dict[str, Any]) -> bool:
    return (state["market_stalls"].get("market", {}).get("keeper_id") == "salma"
            and "market" in state["locations"])


def project_quest_event(state: dict[str, Any], event: DomainEvent, *,
                        rpg_authorized: bool) -> None:
    p = event.data
    player = event.actor_id
    if (not rpg_authorized or set(p) != {"quest_id"}
            or p["quest_id"] != QUEST_ID or not isinstance(player, str)
            or player not in state["entities"]
            or state["entities"][player]["controller"] != "player"
            or not _available(state)):
        raise ValueError("quest requires authorized player and published local fixture")
    if _in_transit(state, player):
        raise ValueError("quest command refused while travelling")
    from .player_foraging import player_forage_signal
    # A scheduled physical forage is also a player action, not free time.
    if any("__player_forage" in s["payload"]
           and s["payload"]["__player_forage"].get("player_id") == player
           for s in state["scheduled"].values()):
        raise ValueError("quest command refused while gathering")
    owned = state["player_quests"].setdefault(player, {})
    if event.event_type == "PlayerQuestAccepted":
        if QUEST_ID in owned:
            raise ValueError("quest may only be accepted once")
        owned[QUEST_ID] = {
            "accepted_at": state["time"], "completed_at": None,
            "evidence_trade_id": None, "claimed_at": None,
            "reward_from_before": None, "reward_from_after": None,
            "reward_to_before": None, "reward_to_after": None,
        }
        return
    if event.event_type != "PlayerQuestRewardClaimed":
        raise ValueError("unsupported player quest event")
    q = owned.get(QUEST_ID)
    if q is None or q["completed_at"] is None or q["claimed_at"] is not None:
        raise ValueError("quest reward requires one proven, unclaimed completion")
    # No teleporting currency: claim at the real stall while its keeper
    # is available. The source has to hold real proceeds before any transfer.
    if (state["entities"][player]["location_id"] != "market"
            or not _present(state, "salma", "market")):
        raise ValueError("reward collection requires a local available keeper")
    donor = state["resources"].get(REWARD_OWNER, {}).get(REWARD_RESOURCE)
    recipient = state["resources"].get(player, {}).get(REWARD_RESOURCE)
    if (not _balance(donor) or not _balance(recipient)
            or donor < REWARD_AMOUNT or recipient + REWARD_AMOUNT > MAX_AMOUNT):
        raise ValueError("quest reward is not funded by actual market proceeds")
    state["resources"][REWARD_OWNER][REWARD_RESOURCE] = donor - REWARD_AMOUNT
    state["resources"][player][REWARD_RESOURCE] = recipient + REWARD_AMOUNT
    q.update({
        "claimed_at": state["time"], "reward_from_before": donor,
        "reward_from_after": donor - REWARD_AMOUNT,
        "reward_to_before": recipient,
        "reward_to_after": recipient + REWARD_AMOUNT,
    })


def track_verified_purchase(state: dict[str, Any], trade_id: str) -> None:
    """Called ONLY after the genuine market reducer has committed its receipt."""
    trade = state["market_trades"][trade_id]
    player = trade["buyer_id"]
    q = state["player_quests"].get(player, {}).get(QUEST_ID)
    if (q is not None and q["completed_at"] is None
            and _qualifying_trade(trade, player)):
        q["completed_at"] = state["time"]
        q["evidence_trade_id"] = trade_id


def player_quest_view(state: Any, player_id: str) -> tuple[dict[str, Any], ...]:
    """Only the player's own quest facts. NPC secrets are not read or returned."""
    raw = state.to_dict()
    if not _available(raw):
        return ()
    q = raw["player_quests"].get(player_id, {}).get(QUEST_ID)
    status = ("available" if q is None else
              "claimed" if q["claimed_at"] is not None else
              "completed" if q["completed_at"] is not None else "accepted")
    return ({
        "quest_id": QUEST_ID, "title": QUEST_TITLE,
        "objective": "Buy at least one real loaf from Salma at the market after accepting.",
        "progress": 1 if q is not None and q["completed_at"] is not None else 0,
        "goal": 1, "status": status,
        "reward": {"resource": REWARD_RESOURCE, "quantity": REWARD_AMOUNT,
                   "source": "market sales"},
        "evidence_trade_id": q["evidence_trade_id"] if q is not None else None,
    },)
