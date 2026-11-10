# PLAY-48S2 — prospective renewable employer food-wage contract (design, NOT implemented)

**Decision state 2026-11-11:** `DESIGN_ONLY / BLOCKED_ON_PLAY48S_48H_EVIDENCE`, PLAY48_OPEN / RELEASE_NO_GO. No production behavior or persistence changes in this document.

## Why the present system cannot claim a lasting wage cycle

The verified `courier_provisions.py` contract is signed only by the trusted operator at time zero (bootstrap required), immediately subtracts **already owned physical food** from a known payer site, and has a fixed maximum of three units per worker. `pay_courier_provision` consumes at most those prepaid units after an authenticated on-site service and stores an immutable receipt. The existing `early_courier_food_wage_enabled` flag only changes **when a previously funded loaf is paid**, not how a new loaf is earned by the employer. PAYING 1+1 wages at t=0 in PLAY-48S therefore proves a finite honest experiment, not an economy with recurring payroll.

At day two of PLAY-48R the actual baker produced nine loaves (versus seven) but resident meals remained six and four residents reached hunger 100. Extra bread was not converted into food access. The market held five food units at the checkpoint, yet the couriers in earlier causal data reached hunger 100 and could not begin trips. The missing mechanism is **explicit local employer authorization to fund wages repeatedly from genuinely acquired inventory, with no remote transfer and no personal-cargo theft**.

## Proposed economy-owned recurring service, subject to review

The merchant/employer signs an opt-in, bounded *service contract* through a versioned authorized event. At each **actually co-located** market encounter following a verified physical courier delivery, the engine may:
1. Check the merchant's personally/business-site **unreserved** surplus stock of real bread, an agreed service rate, the worker's contract, market shift, and a bounded amount per service/day.
2. Reserve **exactly one** unit from the market's durable **owned** `food` stock in the same atomic event/command as the service receipt (or a reviewed equivalent two-step reserve/pay transaction). The recipient gains one personally **owned** loaf, never an entrusted parcel, sale offer or not-yet-produced crop.
3. Write a unique worker/site/service and resource before/after receipt, with exact debit/credit. Reject double funding, service count reuse, unknown stock, worker substitution, remote payer, counterfeit service, negative stock, outstanding sale reservations, and nonconsensual diversion of another NPC's food. Keep 12 known copper invariant.
4. Allow the NPC's **normal autonomous consumption** to eat the personally owned wage, with normal action time and hunger reduction. NEVER set hunger down directly and NEVER ignore the existing `hunger>=90` or fatigue safety constraints.

The contract cannot automatically save a courier **already stranded away from work** with hunger >=90. A separate early genuine, prepaid service and worker food access route (first field water delivery) is needed to avoid the catch-22 before first harvest. Any economic slowdown due to insufficient supply must still occur causally.

## Versioning and trust boundary

Today `CourierProvisionConfigured` is `bootstrap` only, has persisted immutable shape with `created_at=0` and finite `total_units<=3`. **Do NOT** silently relax it to support runtime refills: old schema/rules and save compatibility depend on that. A new event / persisted contract semantics requires explicit prior security review, rules/schema version decision, backward-compatibility rejection or migration policy, and adversarial tests. There must be a strict source-of-authority separation between autonomous NPC market intent and trusted contract settlement.

## Falsifiable acceptance experiments

- P0: PLAY48-S finite A/B CI passes 3.10/3.13, with observed actual wages and unique same-command service receipts.
- P1: a fresh 13-NPC from-genesis case with repeatable **newly produced** bread funds 2+ real later services without any extra genesis food, credit, remote market oracle or time-zero unlimited escrow. Match event-level supply receipts, owned stock, wage, and independent consumption.
- P2: actual wages paid day2/day3, new food purchases and courier routes after hour72. Record counterexample if no recovery; an accepted transaction mechanism is not proof the people are nourished.
- P3: rainfall-water conservation, original 12 copper, 13 people, all food/grain/seed/stock provenance, route presence, no same-tick double work, SQLite replay and reopen.
- P4: deliberately insolvent merchant, drought/no crops, no authenticated service, wrong courier, repeated receipt, stale revision, and duplicate command must **fail closed** without food, copper, wage or event mutation.
- P5: real 96h and 168h independent same-genesis control/treatment with full individual hunger and job statistics, SHA-pinned Python 3.10/3.13 CI, and explicit owner acceptance. Allow genuine bad outcomes. Production release and P0 migration remain separately blocked.

This design does not authorize automatic refills, wages minted from economic activity, state-changing diagnostics, or starting PLAY49.
