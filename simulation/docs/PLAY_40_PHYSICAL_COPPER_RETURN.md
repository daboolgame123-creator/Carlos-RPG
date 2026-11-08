# PLAY-40 — real, finite market receipts return by physical couriers

**Root-cause Issue #24:** [PLAY-39](PLAY_39_TWO_FARM_WATER_BUDGET.md) proved that more water creates another ripe crop but nine people still reach hunger 100 while seven physical loaves sit unsold. The old market credits all consumer payments to the site owning food and does not return earnings to the farm and bakery. This is **an input to solving wages**, not the finished wage mechanism.

## Actual new behavior

The default circuit continues exactly as before: `well→field→bakery→market→bakery→field→well`, one physically moved parcel per leg, 0 remote deliveries. The optional **trusted time-zero** copper-return contract is enabled *only when the physical courier's `coin_copper` balance is explicitly initialized to zero* and the local market, bakery and that courier's field have already initialized their own finite `coin_copper` balances. Existing courier circuits with **unknown** cash slots remain **unable** to carry money.

If physically collected consumer receipts exist in the market stock, a courier at the market can pick up exactly **one existing copper coin** for the real market→bakery road, and deliver it at the bakery. On the bakery→farm road it may carry **one surplus existing bakery coin** to the actual field only if the bakery first retains **at least one coin** in its owned site stock. This simple documented reserve is a bounded first policy, *not a negotiated wage/contract*. Transport is interrupted by the same hunger/fatigue/safety/injury/double-work controls as material parcels; funds stranded in transit remain accounted for physically.

All these actions use existing authenticated `SupplyCargoPicked`, actual scheduled `NPCTravelStarted` and `SupplyCargoDelivered` events, without extra transfer capabilities, central ledger mutation, player omniscience, money minting, instant inter-site credits, new persisted keys or schema shape changes. **Rules version is 54**, Schema remains 40; current-version regression pins and historical workflow checks must follow.

## Success and limits

Two independent farm routes with 9 NPCs, 12 finite copper initial stock and 3 real market loaves. Confirm the sale receipts are what supply the real bakery/farm cash (zero at t=0), including coin held by the courier during a road leg. Assert all-owner totals conserved and receipts accounted exactly, SQLite genesis replay/snapshot, forged remote coin pickup rejected, unknown-cash historical courier unchanged, Python 3.10 and 3.13 targeted & full historical on final SHA.

**Not yet a wage:** The shop still owns bread sale proceeds until real funds are paid to an individual worker with a completed job and an authorized funded local contract. Next phase must model explicit local wage receipts and one-time worker transfer, no paycheck without site-owned available money, no double-pay, no employer forgery, no payment during travel. The zero-cash market will still fail to pay before a real sale; starving villages remain allowed.

DRAFT only until exact final SHA CI success and review. Do not merge `main`.
