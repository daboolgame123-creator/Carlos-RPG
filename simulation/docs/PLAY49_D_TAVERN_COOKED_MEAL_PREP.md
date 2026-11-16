# PLAY49-D — real tavern ingredient meal, pre-stage experimental evidence

Date 2026-11-16. Parent PLAY49-C SHA d9ae1282eb40be58d644625090e917cf94bddf56.
Read-only isolated simulation interfaces; no core engine modifications.

## Finite scenario and provenance
- 4 staffed physical markets, actual 1 fruit from prior orchard harvest and 1
  cheese from consuming 2 finite milk at the dairy, both with real paid wages.
- Huda buys fruit for 1 copper at orchard and cheese for 2 at dairy, and walks
  both purchased items to tavern through established 50s+70s+60s roads.
- A real distinct cook owns a *fixed initial* 5 copper; Salma's original 10
  starting coins were split into Salma 5 + cook 5, so total copper is **unchanged
  relative to parent genesis**, and no coin is minted into the tavern venue.
- Cook pays Huda 2+3 copper for both physically held products. She deposits
  1 personally owned fruit + 1 personally owned cheese into the local tavern
  workshop with existing trusted two-sided workshop deposit receipts.
- The real 300-second compound recipe, once scheduled and completed by a
  physically present cook, consumes both ingredients and generates **one
  actual legacy food** at tavern. It is a genuine edible meal, not a direct
  relabeling of undeposited fruit/cheese or a gift.
- Tavern host quotes this one owned food for 3 copper; Salma walks a real
  80-second bakery→tavern road and pays the venue. That completed sale funds
  the cook's *previously agreed* one-copper wage. Salma eats her own purchased
  food using the existing NPCFoodConsumed event, with real 20→0 hunger relief.
- No free meals, no salary from zero site funds, no extra endogenously minted
  currency; deterministic SQLite exact replay/snapshot/time split tested.

## Limits
All input resources and the 5-copper cook allocation are declared at genesis.
No cattle or renewable milk supply, fruit seasonality, spoilage, auto-trade,
autonomous cook/store actions, unlimited tavern service or village-wide
96/168h sustainability. Single exact test scenario only.
The real 13-NPC world is **not** rescued or changed by this work.

Status: PLAY49_PREPARATION_ONLY / DRAFT_NO_MERGE /
PLAY48_OPEN / RELEASE_NO_GO.
