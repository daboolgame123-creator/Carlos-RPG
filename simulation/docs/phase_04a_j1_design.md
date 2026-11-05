# 04-A/J1 — Property rights foundation, staged development design

**Status:** J1a IMPLEMENTATION SCOPE APPROVED BY USER — design and code in development; J1b/J1c separate future gates.
**Baseline:** 02-H Rules32 / Schema24, green CI 42114734174 at 5b37787dadd226279ed81513efd59ffcca7ade4c.
**Branch:** simulation-engine-phase-04a-j1; no story imports or changes to main.

## Why J1 cannot be a single simplistic ownership mapping

The authoritative inventory map tracks who currently holds the units, not a legal title. The sale reducer and physical taking can both move fungible goods. Without a lot/provenance allocation scheme a naive `rights[item]=owner` would be wrong on splitting, resale, honest purchase of goods mixed with stolen goods, consumption, and production. Accordingly:

### J1a — this slice: immutable original entitlement records ONLY
- Trusted bootstrap configuration at time 0 of a bounded, explicitly known, fully stocked amount, with an independent registered steward for a site account.
- Persist event and immutable record, with source holder, claimant of an initial entitlement, commodity, quantity, and time 0. No change to stock. Reject unknown/undefined balances, doubled registrations for the same source/item that exceed physical stock, self-contradicting site title, unauthorized nonbootstrap, unknown actor and malformed input.
- This is *historical registered evidence*, not universal legal title, current title, permission, adjudication, restitution or criminal guilt. If the item moves, the origin record does NOT move or prove where a specific anonymous unit went. Do not expose it to NPCs via player view.
- Later sales and takings do not rewrite the origin. Origin trace exists to inform future provenance-aware lot model. No automatic title inference from balance.
- Schema25/Rules33, strict refusal to open real Schema24/Rules32 old saves unchanged. No migration. Full replay, snapshot, rollback and 7-NPC tests.

### J1b — future separate slice: physical lots and movement allocation
- Define identity of lots or bounded quantity portions when bread is indistinguishable; no inventing item IDs for historical balances.
- Source-aware lot allocation and immutable movement provenance for each transfer channel: market, taking, gifts, production, consumption, and loans where applicable.
- Only then consider derived `current_custody` for a registered lot; if any unsupported movement touches it, reject/make provenance explicitly unknown, never guess.

### J1c — future separate slice: permission and transfer of legally defined rights
- Record positive and negative grants/limits, expiration/revocation, consent, owner/title transfer and contingent rights. A title claim is NOT automatically proven by event narration; law code and jurisdiction still required.
- Only after J1b may we state current registered entitlement independently from physical possession. Adjudication, jurisdiction, witnesses' awareness and execution remain outside J1.

## Seven-person adversarial acceptance
- Authorized bakery steward registers 2 bread units as origin of an entitlement at bootstrap; inventory remains 2; another overlapping registration totalling 3 is rejected.
- NPC Basim takes 1 bread later; bakery physically retains 1 but the origin record remains historical 2 with an explicit *origin only* type; no guilt, stolen title inference or automatic reclamation.
- Market buyer buys 1 unit; origin record does not become proof of ownership by buyer or seller; goods and copper behave exactly as before.
- Unknown owner/site, uninitialized balance, negative/overflow, duplicate identity or unsupported item/currency; rejected without state mutation.
- Trusted bootstrap cannot create origin records after time 0; untrusted events cannot. A malicious snapshot cannot forge invalid quantities or provenance.
- Older Schema24/Rules32 world stays byte-identical upon explicit refusal. Existing behavior semantic parity of opt-in-off world unchanged.

## Risks and gates
- All registered rights are historical evidence only, not effective present legal ownership. This is intentionally less ambitious than a court: **no law code, jurisdiction, punishment, or legal title transfer**.
- Existing 02-H complaint, witness and possession remain untouched.
- External independent review and P0 production backup/recovery are open. Do not import real Carlos world.
