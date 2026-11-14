"""PLAY48 read-only employer cash settlement: no wages or coins are created."""
from __future__ import annotations
from dataclasses import dataclass
from .economic_diagnostics import audit_npc_economy

CASH = "coin_copper"

@dataclass(frozen=True)
class SiteSettlement:
    site: str
    known_copper: int | None
    completed_unpaid_signed_wages: int
    unpaid_job_ids: tuple[str, ...]
    cash_after_earned_unpaid_wages: int | None
    cash_shortfall_for_completed_wages: int | None
    physical_courier_cash_destined_here: int
    historical_site_customer_revenue: int
    historical_work_wages_paid: int
    historical_sale_service_wages_paid: int

    @property
    def uncommitted_cash_estimate(self) -> int | None:
        """NOT authorization to pay: physical routes and future costs are not modeled."""
        if self.cash_after_earned_unpaid_wages is None:
            return None
        return max(0, self.cash_after_earned_unpaid_wages)

@dataclass(frozen=True)
class CashSettlementReport:
    total_known_copper: int
    copper_scope_complete: bool
    unknown_coin_owners: tuple[str, ...]
    npc_personal_copper: int
    site_owned_copper: int
    courier_cash_custody: int
    sites: tuple[SiteSettlement, ...]

def audit_completed_work_cash_settlement(state) -> CashSettlementReport:
    """Read existing true owners, finished unpaid job receipts and carried cargo.

    A salary is not due for hypothetical future jobs. Previously paid wages
    are NOT due twice. Cargo in a courier's physical slot is not money owned
    by that courier personally or already delivered into a site till.
    """
    money=audit_npc_economy(state)
    inventory, jobs, recipes=state.resources, state.production_jobs, state.production_recipes
    in_custody={site:0 for site in state.locations}
    courier_cash=0
    for who,c in sorted(state.supply_circuits.items()):
        cargo=c.get("carry")
        if cargo is None or cargo["resource"] != CASH:
            continue
        amount=inventory.get(who, {}).get(CASH)
        if type(amount) is not int or amount != 1:
            raise ValueError("in-flight copper needs one real carried unit")
        dest=cargo["destination"]
        if dest not in state.locations:
            raise ValueError("copper cargo needs a real site destination")
        in_custody[dest]+=1
        courier_cash+=1

    sites=[]
    for site in sorted(state.locations):
        cash=inventory.get(site, {}).get(CASH)
        if cash is not None and (type(cash) is not int or cash < 0):
            raise ValueError("site copper cannot be guessed or negative")
        due,paid,unpaid=0,0,[]
        for jid,j in sorted(jobs.items()):
            if j["site_id"]!=site or j["status"]!="completed":
                continue
            contracted=recipes[j["recipe_id"]].get("wage_coin")
            if "work_wage" in j:
                paid+=j["work_wage"]["amount"]
            elif contracted is not None:
                if type(contracted) is not int or contracted <= 0:
                    raise ValueError("signed cash wage must be positive integer")
                due+=contracted
                unpaid.append(jid)
        revenue,service_paid=0,0
        for trade in state.market_trades.values():
            if trade["stock_owner_id"]==site and trade["payment_resource"]==CASH:
                revenue+=trade["total_paid"]
                service_paid+=trade.get("keeper_commission_coin",0)
        remaining=(cash-due if cash is not None else None)
        sites.append(SiteSettlement(
            site=site,known_copper=cash,
            completed_unpaid_signed_wages=due,
            unpaid_job_ids=tuple(unpaid),
            cash_after_earned_unpaid_wages=remaining,
            cash_shortfall_for_completed_wages=(max(0,-remaining) if remaining is not None else None),
            physical_courier_cash_destined_here=in_custody[site],
            historical_site_customer_revenue=revenue,
            historical_work_wages_paid=paid,
            historical_sale_service_wages_paid=service_paid
        ))
    return CashSettlementReport(
        total_known_copper=money["copper_known_total"],
        copper_scope_complete=money["copper_scope_complete"],
        unknown_coin_owners=money["copper_unknown_owners"],
        npc_personal_copper=sum(inventory.get(who,{}).get(CASH,0) or 0 for who in state.npcs),
        site_owned_copper=sum(row.known_copper or 0 for row in sites),
        courier_cash_custody=courier_cash,
        sites=tuple(sites),
    )
