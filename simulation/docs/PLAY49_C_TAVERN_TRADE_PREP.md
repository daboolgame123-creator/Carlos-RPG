# PLAY-49-C — real merchandise for a tavern, test-only

Created 2026-11-16 from isolated PLAY49-B, NOT OpenCode's active PLAY48 branch.
No engine/core files are changed and this is a DRAFT, NOT a stage transition.

## Actual tested causal chain
- The already finite orchard and dairy genuinely produce exactly one fruit
  and one cheese (plus the bakery's existing product). Production takes time
  and is funded by the existing already-declared owner wallets at genesis.
- Existing resident Huda uses her **OWN opening 10 copper** to purchase fruit
  for 1 at the orchard and cheese for 2 at the dairy, walking the 50/70-second
  roads. 3 copper moves to the sellers' **site-owned balances**.
- Huda carries her **personally owned inventory** through the 60-second
  dairy-to-tavern road and posts locally visible quotes at the tavern, fruit
  for 2 and cheese for 3. The separate tavern venue has an on-site host,
  and starts with **zero fruit, cheese and copper**. Huda cannot sell
  stock owned by the host or the tavern.
- Salma travels 80 real seconds to the tavern; pays her own copper for both
  real items. Huda receives 5 copper, so **Huda's net realized profit is
  +2 copper**, not a fabricated wage. All four market transfers are
  source-backed, replay-verified, physically co-located, conserved and
  time-split invariant.
- No new copper or food is created by tavern bootstrap. Fraud tests reject
  no-stock venue sales, false owner claims, remote/in-transit sales,
  overselling a customer's unit and second sale of the filled quote.

## Important exclusions
This is procurement and **resale** at a tavern, not completed tavern cooking,
a profitable staffed hospitality service, real nutrition, staff wage, or
autonomous recurring merchant demand. Huda manually undertakes trades in
a trusted test scenario; the original village AI is unchanged. Actual
baking/cooking must consume a legitimate physical inventory at the local
kitchen using supported ownership transfer, and wages must come from real
revenue; those are NOT proven here. No auto-fed villagers or free meals.
Later stages need periodic crop/milk sourcing, recipes, demand, labor,
maintenance and 96/168h observed economy under autonomous NPC decisions.

STATUS: PLAY49_PREPARATION_ONLY / DRAFT_NO_MERGE /
PLAY48_OPEN / RELEASE_NO_GO. No main merge or unapproved stage closure.
