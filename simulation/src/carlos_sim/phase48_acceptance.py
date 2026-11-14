"""PLAY-48 read-only, independent acceptance gates for an authentic 13-NPC economy.

This module can reject a candidate that passes ordinary code tests but fails
actual wages, buying, eating or cargo transport. It NEVER advances a world,
mutates any owner balances or certifies an economic engine's event provenance.
External real-world-source, conservation, replay and CI evidence must be
supplied separately; synthetic unit tests prove the checker, not the village.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .economic_diagnostics import audit_npc_economy

HOURS = (36, 48, 72, 96, 120, 144, 168)
LATE_HOURS = (96, 120, 144, 168)
REQUIRED_COURIERS = ("hana", "huda")
EXPECTED_NPCS = 13
EXPECTED_COPPER = 12


@dataclass(frozen=True)
class EconomicCheckpoint:
    hour: int
    resident_ids: tuple[str, ...]
    hunger100: tuple[str, ...]
    known_copper: int
    copper_scope_complete: bool
    npc_copper: int
    site_copper: int
    other_copper: int
    npc_food: int
    completed_production: int
    food_trades: int
    consumed_meals: int
    paid_work_receipts: int
    paid_food_work_receipts: int
    paid_courier_receipts: int
    courier_deliveries: tuple[tuple[str, int], ...]

    @property
    def earned_receipts(self) -> int:
        return (self.paid_work_receipts + self.paid_food_work_receipts
                + self.paid_courier_receipts)

    def deliveries(self, who: str) -> int:
        return dict(self.courier_deliveries).get(who, -1)


def checkpoint_from_state(state) -> EconomicCheckpoint:
    """Inspect one persisted checkpoint without creating any game events.

    This function cannot prove initial provenance, travel co-presence or
    resource conservation on its own. Inspect the canonical event store,
    independent source seed, and full physical conservation too.
    """
    if type(state.time) is not int or state.time < 0 or state.time % 3600:
        raise ValueError("economic gate requires an exact nonnegative hour")
    audit = audit_npc_economy(state)
    owned = audit["copper_known_by_owner"]
    residents = tuple(sorted(state.npcs))
    npc_cash = sum(owned.get(n, 0) for n in residents)
    site_cash = sum(owned.get(n, 0) for n in state.locations)
    other_cash = audit["copper_known_total"] - npc_cash - site_cash
    if set(residents) & set(state.locations):
        raise ValueError("NPC identity collides with the site cash scope")
    paid = [job for job in state.production_jobs.values()
            if job["status"] == "completed"]
    deliveries = tuple(
        (who, state.supply_circuits[who]["deliveries"])
        if who in state.supply_circuits else (who, -1)
        for who in REQUIRED_COURIERS
    )
    return EconomicCheckpoint(
        hour=state.time // 3600,
        resident_ids=residents,
        hunger100=tuple(sorted(
            who for who in residents if state.npcs[who]["needs"]["hunger"] == 100
        )),
        known_copper=audit["copper_known_total"],
        copper_scope_complete=audit["copper_scope_complete"],
        npc_copper=npc_cash,
        site_copper=site_cash,
        other_copper=other_cash,
        npc_food=sum(state.resources.get(who, {}).get("food", 0)
                     for who in residents),
        completed_production=len(paid),
        food_trades=sum(t["resource"] == "food"
                        for t in state.market_trades.values()),
        consumed_meals=len(state.consumptions),
        paid_work_receipts=sum("work_wage" in j for j in paid),
        paid_food_work_receipts=sum("food_wage" in j for j in paid),
        paid_courier_receipts=sum(
            len(p["payments"]) for p in state.courier_provisions.values()
        ),
        courier_deliveries=deliveries,
    )


@dataclass(frozen=True)
class IndependentEvidence:
    """External verification must be documented with exact head and run IDs.

    False is the safe default; accepting arbitrary True values here is NOT
    equivalent to verifying the canonical SQLite event or CI records.
    """
    original_same_genesis: bool = False
    physical_resources_conserved: bool = False
    sqlite_replay_and_integrity: bool = False
    historical_save_rules_compatibility: bool = False
    same_head_dual_python_full_ci: bool = False

    def complete(self) -> bool:
        return all((
            self.original_same_genesis,
            self.physical_resources_conserved,
            self.sqlite_replay_and_integrity,
            self.historical_save_rules_compatibility,
            self.same_head_dual_python_full_ci,
        ))


@dataclass(frozen=True)
class AcceptanceResult:
    status: str
    failures: tuple[str, ...]

    @property
    def eligible_for_independent_review(self) -> bool:
        return self.status == "METRICS_MET_AWAITING_HUMAN_RELEASE_REVIEW"


def evaluate_play48(
    candidate: Mapping[int, EconomicCheckpoint],
    control: Mapping[int, EconomicCheckpoint],
    *,
    evidence: IndependentEvidence = IndependentEvidence(),
) -> AcceptanceResult:
    """Fail-closed 36/48/72/96/120/144/168h numeric and provenance gate.

    The numerical gate is deliberately necessary but not sufficient for
    approval: no one can label PLAY48_GO from snapshots alone.
    """
    failures: list[str] = []
    missing = [h for h in HOURS if h not in candidate or h not in control]
    if missing:
        failures.append(f"missing_same_hour_control_candidate={missing}")
    if not evidence.complete():
        failures.append("independent_genesis_conservation_replay_versions_CI_incomplete")

    expected_residents = candidate[36].resident_ids if 36 in candidate else ()
    for hour in HOURS:
        for name, rows in (("control", control), ("candidate", candidate)):
            if hour not in rows:
                continue
            x = rows[hour]
            if x.hour != hour:
                failures.append(f"{name}:wrong_hour:{hour}")
            if (len(x.resident_ids) != EXPECTED_NPCS
                    or len(set(x.resident_ids)) != EXPECTED_NPCS
                    or (expected_residents and x.resident_ids != expected_residents)):
                failures.append(f"{name}:NPC_identity_mismatch:{hour}")
            if not x.copper_scope_complete or x.known_copper != EXPECTED_COPPER:
                failures.append(f"{name}:original_12_copper_not_proven:{hour}")
            if (min(x.npc_copper, x.site_copper, x.other_copper, x.npc_food) < 0
                    or (x.npc_copper + x.site_copper + x.other_copper
                        != x.known_copper)):
                failures.append(f"{name}:invalid_owner_cash_partition:{hour}")
            if any(x.deliveries(who) < 0 for who in REQUIRED_COURIERS):
                failures.append(f"{name}:missing_real_courier:{hour}")

    for hour in (48, 72):
        if hour not in candidate or hour not in control:
            continue
        new, old = candidate[hour], control[hour]
        for metric in ("food_trades", "consumed_meals"):
            if getattr(new, metric) < getattr(old, metric):
                failures.append(f"regression_{metric}:{hour}")
        for who in REQUIRED_COURIERS:
            if new.deliveries(who) < old.deliveries(who):
                failures.append(f"regression_loaded_delivery_{who}:{hour}")

    # A formerly cash-starved village must regain *actual earning*, rather
    # than merely change nominal prices or hold unsold producer stock.
    if 36 in candidate and 48 in candidate:
        prev, x = candidate[36], candidate[48]
        if (x.npc_copper + x.npc_food == 0
                and x.earned_receipts <= prev.earned_receipts):
            failures.append("48h_no_personal_food_cash_or_new_wage_receipt")

    for hour in (72, *LATE_HOURS):
        if hour in candidate and candidate[hour].hunger100:
            failures.append(f"hunger100:{hour}:{','.join(candidate[hour].hunger100)}")

    for prev_hour, hour in zip(HOURS, HOURS[1:]):
        if prev_hour not in candidate or hour not in candidate:
            continue
        x, prior = candidate[hour], candidate[prev_hour]
        for metric in ("completed_production", "food_trades", "consumed_meals",
                       "paid_work_receipts", "paid_food_work_receipts",
                       "paid_courier_receipts"):
            if getattr(x, metric) < getattr(prior, metric):
                failures.append(f"nonmonotone_{metric}:{prev_hour}-{hour}")
        for who in REQUIRED_COURIERS:
            if x.deliveries(who) < prior.deliveries(who):
                failures.append(f"nonmonotone_{who}_deliveries:{prev_hour}-{hour}")

    if 72 in candidate and 168 in candidate:
        old, end = candidate[72], candidate[168]
        for metric in ("completed_production", "food_trades", "consumed_meals",
                       "earned_receipts"):
            if getattr(end, metric) <= getattr(old, metric):
                failures.append(f"no_real_post72_{metric}")
        for who in REQUIRED_COURIERS:
            if end.deliveries(who) <= old.deliveries(who):
                failures.append(f"no_real_post72_{who}_cargo")
    if failures:
        return AcceptanceResult("PLAY48_ECONOMIC_NO_GO", tuple(sorted(set(failures))))
    return AcceptanceResult("METRICS_MET_AWAITING_HUMAN_RELEASE_REVIEW", ())
