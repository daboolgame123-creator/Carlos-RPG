# PLAY49-H — finite, water-fed third meal (isolated experiment)

Date: 2026-11-17. Parent: PLAY49-G exact SHA `0ae9b6a89face49050fa0452b53e40432d724b3f`.
Branch: `experiment/play49-water-fed-renewal-cycle-20261117`.
Status: **PLAY49_PREPARATION_ONLY / PLAY48_OPEN / RELEASE_NO_GO / DRAFT_NO_MERGE**.

## Causal hypothesis and controls

The two initial genuine meals in PLAY49-G exhausted the opening two ripe fruit and four milk. A third real meal must not be produced by supplying an unexplained runtime stock reset. The first experiment uses *existing engine rules only*:

- The orchard receives at trusted time zero **one seed, a hoe, one water unit and empty planted/ripe field balances**, plus one additional authenticated planting and harvesting recipe. A local farmer plants, an authorized agriculture command consumes exactly one water unit, and the engine's existing scheduled 24-hour crop maturation produces one ripe crop and returns one viable seed, subject to soil capacity one. A timed harvest converts the ripe crop into the market's existing `fruit` inventory.
- The dairy receives at trusted time zero one physically represented cow (a production tool), exactly one feed and one water. The cheesemaker spends both feed and water in a **7200-second compound milking recipe**, obtaining two milk to turn into one cheese in a separate timed job. Cow ownership persists; feed and water do not.
- None of the eight new source balances is modified by `ResourceChanged` after time zero; runtime resources result only from authorized production and the authenticated clock/plot rules. This trial does not purport to model animal lactation biology, automatic weather, irrigation, forage regeneration or an unlimited dairy.
- Huda must walk tavern → dairy → orchard → dairy → tavern before buying both new real products using her two truly owned remaining copper. Independent sellers receive that copper; Huda brings both products and sells them for 2+3 copper to the tavern, whose actual existing treasury is debited 5 copper. Cooking consumes the two goods in 300 seconds; Huda buys a third plate with her actual 5 copper at the third-cycle listed price 5. The tavern then settles all still-unpaid completed signed production cash wages, bounded by each employer's actual wallet.

## Expected checks

- Crop growth before planting or a second simultaneous growth is refused without mutating SQLite.
- No milk without known feed and water, no cheese without milk, no fruit before a grown/harvested crop, and no physically distant buy.
- Total copper stays at 22 across all owners, with site/person ownership kept distinct. The last tavern balance should be 4 coins after a real earned cook wage.
- Crop count is exactly one and orchard water and dairy feed/water are zero at end: **a fourth meal is NOT proved**.
- Deterministic event replay, snapshot and SQLite integrity must agree with the actual last state.

## Unproven / release gates

This is a *commanded*, test-only third batch and a first regrowth viability check; it is **not autonomous NPC agriculture or commerce**. In particular no automatic feed/water replenishment, 96h/168h economic survival, multi-day profitable equilibrium, annual world history or old-version save acceptance is claimed. Adding the new G persisted site-purchase receipt still requires separate save/schema compatibility evaluation. No core runtime or world-version changes in this H branch; it inherits the unapproved G parent behavior.

Require exact-HEAD Python 3.10/3.13 focused workflow and full regression before accepting even this experimental result. Wait for PLAY48's real 13-NPC acceptance before any PLAY49 integration or release.
