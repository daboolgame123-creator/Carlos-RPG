# PLAY49-G experimental venue-owned financing of a second real cooked meal

2026-11-17 isolated experiment; base SHA 5464f12efacc825fdd8bf1fb03b8d773b9f65935.
**Prototype reducer change** to \`MarketTradeExecuted\` when an explicitly
registered present merchant purchases real local recipe ingredients from a
different owner in the name of a site. Trade receipt retains the original
double-entry geometry, with an additional \`business_keeper_id\` proof field.

## New prototype contract
- Only real on-site registered merchant at the actual workshop may make
  a \`buy_for_site\` call, against an actual physically present other seller.
- Buyer is the SITE inventory and SITE wallet, not the private NPC purse.
- Goods must be explicitly required inputs to a configured local production
  recipe. Cash must be known, sufficient, and reserve the already-earned
  unpaid site wages. No teleporting, credit, overdraft, fabricated stock,
  commodity minting or old consumer bypass.
- Events are recorded and replayed with the existing \`market_authorized\`
  command capability; exact per-purchase double-entry balances verified.
- Existing NPC and player trade calls preserve their old event fields and
  trusted service contract unchanged.
- Every business receipt records \`business_keeper_id\`, and historical
  market trade validation permits only that extra field with exact onsite
  worker/recipe/stall consistency.

## Two-cycle finite trial
- At genesis: **two finite ready orchard fruits and four finite dairy
  milk units**, not unlimited supply, plus the existing 22 owned copper.
- First actual ingredient purchases and one 300s plate: the original cook
  spends 5 personally owned copper, earns one 1c site wage after customer
  Huda pays 6c. After payroll the venue has **5c**.
- Two additional actual timed fruit/cheese production jobs consume the
  remaining original finite raw inputs. Huda traverses real roads, pays
  sellers from her own remaining purse, and personally carries the goods
  to the tavern.
- A new actual site purchase spends 2+3 **SITE copper** for Huda's owned
  goods, depositing BOTH ingredients directly into the genuine tavern
  warehouse. The cook does **not** receive Huda's cash and does not
  personally buy the second batch.
- 300 more seconds makes one actual second plate, which is paid for by
  Huda (6c) from her genuine trade proceeds; one new signed earned cook
  wage (1c) is settled. Site retains 5c and the cook ends with 2c.
  Total copper and owner provenance conserved exactly.
- No automatic food replenishment, shopkeeping or buying NPC AI and no
  96/168h village claim. Production ends after the two real raw batches.

## Safety / integration
This is not a staged production release or approved stable save rule.
The added persisted receipt shape means **Rules/schema compatibility and
authentic predecessor save tests are required before any merge**. Do not
merge into active PLAY48, main or modify OpenCode. A separately isolated
full historical CI must pass exact head before the experimental contract
can be treated as technically validated.
Status: PLAY49_PREPARATION_ONLY / DRAFT_NO_MERGE /
PLAY48_OPEN / RELEASE_NO_GO.
