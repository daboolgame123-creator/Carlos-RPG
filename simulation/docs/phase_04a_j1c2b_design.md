# Phase 04-A / J1c2b — legal title feasibility and minimum implementation contract

**Opened:** 2026-11-06. **Status: ANALYSIS / DESIGN IN PROGRESS — NO CODE, SCHEMA CHANGE OR TITLE EVENTS YET.**

## Entry gate

J1c2a closed technically under the owner's explicitly revised independent-review deferral policy, see `phase_04a_j1c2a_closure_gate.md`. Its external review is deferred, not approved; P0 production recovery and unauthenticated network/player commands remain restricted. This design concerns isolated disposable-world engine development only.

## Problem to solve

A physical bread transaction (`MarketTradeExecuted`), taking (`PropertyTaken`), physical custody, J1a recorded origin, J1c1 permission, and J1c2a historical claim transfer are different facts. **None alone grants enforceable current legal title.** A title system needs (1) normative jurisdiction/rules, (2) legally meaningful assignment basis and time, (3) evidence of consent/capability, (4) treatment of theft and good-faith third parties, and (5) a disputed/unknown outcome instead of inventing a winner.

## Proposed deliberately narrow first executable slice (not yet approved as a law)

- One jurisdiction version per explicitly configured local site; no global or implicit inherited law, and no retroactive interpretation of old events.
- A **title assertion/record**, not automatically adjudicated legal title, may cite a real source event and a limited quantity. This is a legal *claim* under a configured rule, not a court verdict.
- Differentiate `unknown`, `uncontested recorded claim`, `disputed`, `settled by explicitly authorized process`. No omniscient lawful-owner field.
- No physical transfer, possession change, market money movement or restitution is triggered merely by writing or disputing a claim.
- Scope to one identifiable registered origin and non-fungible/traceable units where data permits; mixed indistinguishable bread **must be unresolved**, not silently allocated. Never produce more legally recognized quantity than provenance supports.
- Only trusted local authorized bootstrapping for jurisdiction configuration. Never accept free player-supplied role/authority flags from an untrusted API.
- A claimant's statement or sale record alone does not bind a non-consenting third party or defeat an earlier recorded right.
- Keep code/data version pinning, event-source provenance, immutable past, deterministic replay, fail-closed loads for old schema without explicit migration.

## Decisions required before creating a binding title event

1. **Jurisdiction**: initial authority will be local custom, council, lord, or other political institution? A jurisdiction must be explicitly installed in the world and scoped to a place; do not assume a universal court.
2. **Normative transfer rule**: does a consensual market sale transfer lawful title; under which seller entitlement and witness/consent criteria? Does transfer of a *historical claim* ever confer title? Default answer is **NO** until a rule is approved.
3. **Unlawfully removed objects / good-faith buyer**: competing owner, possessor, third-party buyer; unknown/disputed is allowed rather than automatic favoring.
4. **Evidence and disposition**: who may record declarations, object, and resolve claims, and what can the resolver actually know? No court/decision code until institutions J2/J3 are built and bounded.
5. **Title representation**: can the world attribute individual item lots accurately? Otherwise restrict the first slice to a record of conflicting claims, leaving title unresolved.
6. **Historical applicability**: configure rules prospectively with version and effective simulation time. Never infer title from legacy events without authorized migration/design.

## Proposed acceptance tests after approval, before implementation

1. Bakery records origin for two bread units; J1c2a assignment to Salma changes the historical claim ledger, but **does not** mint legal title.
2. Basim takes bread physically; possession/custody changes while legal status remains unknown/disputed.
3. Basim sells to Nora after taking; payment and inventory change, but Nora does not automatically receive enforceable title.
4. Two conflicting claims to the same mixed bread cannot both be granted an enforceable exclusive title; absence of provenance returns unresolved.
5. Invalid site, jurisdiction, actor, authorization, quantity, time, duplicate command or stale revision fail without modifying world.
6. Claim notice never communicates instantly to an absent NPC; gossip/claim does not create omniscient knowledge.
7. Snapshot/replay/full SQLite verification, duplicates and transactional rollback preserve exact provenance and prevent double allocation.
8. Genuine older world is rejected unchanged unless a tested migration has been separately designed; earlier feature-off behavior remains equivalent.
9. Backup + disposable-world restore verifies exact claim state and no physical inventory movement.
10. Both Python 3.10 and 3.13 specialized and full CI pass on exact final code SHA; external review deferred as stated by owner and external environment tests logged.

## Boundaries

**Explicitly excluded:** courts, trials, sentences, police powers, seizure, automatic restitution, legal punishments, fines, state taxes, appeals, fabricated witnesses, and omniscient verification. These require later J2–J5 decisions. No modification to `main` or original Carlos narrative files. No public network access or production save authorization.

## Immediate next engineering action

Perform a constrained audit of existing `market.py`, `rights.py`, `property.py`, `registered_claims.py`, and source-event schemas, then freeze a signed-off minimal normative jurisdiction and title representation contract. **Do not write binding title reducers or migrate Schema 28 / Rules 36 until normative rules are explicitly chosen and verified not to contradict world governance.**


## Initial source-contract audit (2026-11-06)

Read the actual current engine modules `market.py`, `rights.py`, `property.py`, and `registered_claims.py` on the J1 branch:

| Module | Verified contract | Title implication |
|---|---|---|
| `market.py` | Local offers and atomic physical goods/payment balance transfer; site stewards represent the **site's** stock | Payment and receipt are evidence of transaction only; do not determine legally valid title |
| `rights.py` | Trusted time-zero historical original claim, bounded by known registered stock, explicitly `historical_origin_only` | Does not establish contemporary title |
| `property.py` | Physically conserved non-consensual taking requiring an internal capability; no automatic guilt or confiscation | Changes possession, not legal status |
| `registered_claims.py` | Bounded recorded-claim balances, local offer/accept/cancel handshake and provenance | Transfers registered historical claim only, no physical or legal-title movement |

**Audit conclusion:** It would be an unsound implementation to auto-issue `CurrentLegalTitleTransferred` on any of these existing events. The first safe J1c2b implementation cannot be chosen until an explicit law authority, prospective effect, reliable lot identification and evidence/consent representation are fixed. The status is **DESIGN_IN_PROGRESS**, not code-complete; no unresolved audit item is hidden.


## Initial non-normative implementation slice (2026-11-06)

A first **read-only provenance inventory** was introduced without defining a jurisdiction, court, binding title or new legal event: `simulation/src/carlos_sim/title_evidence.py`. It accepts only a trusted engine `WorldState` and an existing J1a registered origin, returning historical registered balances, accepted assignments and live open offers. The fields `legal_title_status="undetermined"`, `legally_enforceable_owner=None`, and `legal_rule_applied=None` **must never be interpreted as a judicial finding**. It must not be sent unfiltered to a player's interface, because this internal object may disclose records outside their knowledge.

Tests: `simulation/tests/test_title_evidence_04a_j1c2b.py` (original registration, consensual reassignment, physical taking and resale, missing origin, snapshot/replay consistency). They verify read-only behavior and no accidental legal-title inference. Commit introducing tests: `df86a0953fb9ddf53791b77c6a160bb708b92d38`. CI results must be verified on this exact code commit before marking these tests passed.

**Remaining unresolved scope:** prospective law and political authority, lawful transfer semantics, mixed-lot provenance and contested claims. Binding legal-title state/events remain intentionally unimplemented. Schema 28 / Rules 36 unchanged. This does not close J1c2b.


## Follow-up evidence packet (2026-11-06)

- `title_evidence.origin_evidence_packet` now places **historical registered claim evidence** beside **physically certified custody**, with the streams explicitly distinct. It never computes `legally_enforceable_owner`, applies a legal law, or resolves competing property rights.
- When the existing J1b custody reducer marks fungible units as `unresolved_quantity`, the packet reports `provenance_certainty="partial_or_unknown"`, never guesses who physically has the specific origin item. `exited_quantity` is separately counted.
- It preserves physical movement audit provenance but exposes the packet **only to trusted internal auditors**; it is forbidden as a direct response to player/NPC/LLM/untrusted interfaces without a knowledge-filtered authorized adapter.
- Three tests cover historical claimant versus real physical holder, mixed/uncertain physical provenance, and replay equivalence/read-only behavior, at test-code commit `15608bf0477babeefa203531f4012a8a837dd50a`. CI requires exact-commit verification. Schema/Rules remain 28/36; no legal title write commands or legislation exist.


## Read-only evidence hardening (2026-11-06)

Three additional regression probes were added in commit `f40917d92781d1eb1e9f9490c3f0fa268940865d`:
1. A once-open offer whose simulated expiry passes is omitted from **active** evidence without rewriting the historical record or creating a legal owner.
2. Mutating returned evidence dictionaries/lists cannot mutate the frozen world, its persistent log or subsequent evidence results.
3. Two origins whose registered quantities share one physical stock source are reported separately; neither generates an enforceable legal owner.

The previous five tests passed as part of the 910/910 full CI for Python 3.10 and 3.13 on code commit `df86a0953fb9ddf53791b77c6a160bb708b92d38` ([CI 42210094258](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42210094258)); adversarial and recovery checks passed as well ([CI 42210094189](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42210094189)). The **three new probes require fresh exact-commit CI**, and must not be called successful before observed.

The remaining normative decision is **not** an implementation bug: local legal rules/authority, item provenance and disposition of contested legal title have intentionally not been defined. J1c2b remains OPEN.


## Historical offer audit completeness (2026-11-06)

- The read-only historical evidence function now emits `historical_assignment_offer_history` for **all** registered offers associated with the selected origin. It retains source account, recipient, quantity, creation, expiry and resolution times plus both `recorded_status` and `effective_status`.
- A logically expired `open` offer is labeled `effective_status="expired"` **without rewriting the event record or stored status**; accepted offers do not become expired afterward, and cancelled offers remain cancelled. `open_historical_assignment_offers` continues to mean strictly still-active offers.
- These observations are an internal auditor-only history and do not infer legal title, change actual goods/claims or grant the player omniscient knowledge.
- Code commit `2afa8ce35896ab8eead9ffd414d0476b7256d925`; four new targeted historical integrity probes at `e425322780dd071bbb4c758f51e884205efc83f1`. The previous exact-code CI [42213953492](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42213953492) completed **916/916** on 3.10/3.13 and companion [42213953544](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42213953544) completed SUCCESS; **new feature verification must use new SHA results**.
- The J1c2b binding legal-title, jurisdiction and adjudication decisions remain UNSPECIFIED; read-only evidence is not adjudication. Do not label entire J1c2b complete.


## J1c2b factual allegations audit — no legal adjudication (2026-11-06)

Added `property_claim_audit_packet(state, claim_id)` in `title_evidence.py`. This trusted-only, read-only report distinguishes an unverified NPC assertion (`property_claims`) from an existing cited physical taking (`property_takings`). A witness-backed allegation can corroborate the **physical action only**, never ownership, legal culpability or enforceable title.

**Important provenance limitation:** existing `property_claims` have no `origin_id`. The auditor must **not** associate a claim with a specific registered provenance lot just because the site, resource or time appears similar. The explicit return is `registered_origin_id=None`, `origin_linkage="not_established"`, `legally_enforceable_owner=None`, `guilt_determined=False`. A missing claim is rejected without mutation. Results stay restricted to trusted internal audit; they are not player/LLM/public views.

Code commit `9fa113a191ab724df4bc2a46c3d766777421d022`; four additional tests commit `09b0f8a4892d6280397186aa7b841c85710ceb9d` (false accusation, actual witnessed taking only, unknown IDs, read-only snapshots/full replay). New CI must pass before this slice is marked verified. No Schema/Rules changes; binding legal-title and local law remain undefined. Stage J1c2b stays OPEN.


## Local comparison of unproven property statements (2026-11-06)

Added `property_claim_context_packet` to the trusted-only read-only audit layer. It accepts an **existing claim ID**, displays its already filed statement and lists other claims filed about the same **site and resource**, ordered deterministically by filing time and claim ID. **Shared site and resource are search filters, not evidence of the same object, incident, contradiction, culpability or legal ownership.** Output explicitly marks each possible comparison with `same_physical_incident_established=False`, `same_registered_origin_established=False` and `conflict_determined=False`.

- No data migration, simulated action or legal rule was added. The auditor reports only facts available to the trusted engine, not knowledge available to a character.
- Code `b8ce3865fb9ba952b089260fd27d16d0930513ff`; four additional tests `93c82401d66e3f694f9168bd7e77130bef3e7b5a` cover apparent competing claims, different filing times, unrelated resource exclusion and immutable replay.
- **Do not claim the additional tests passed until GitHub Actions results on the exact code SHA are verified.** Earlier 924/924 suites on code `09b0f8a4892d6280397186aa7b841c85710ceb9d` finished SUCCESS on Python 3.10 and 3.13 ([CI 42217038655](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42217038655)).
- Binding legal-title adjudication still requires a separately defined local law, validated source evidence and explicit authority. J1c2b remains OPEN.


## Exact physical-incident evidence grouping (2026-11-06)

Added `physical_incident_audit_packet(state, taking_id)` as a **trusted-internal read-only projection**. Unlike location/resource comparisons, a claim that explicitly cites an existing taking ID is linked to that *particular physical action*, with dedicated eyewitness records and chronological claim references. This is grounded in existing `PropertyTaken`/`property_sightings`/`property_claims` event identity and requires no schema/version change.

The packet explicitly **excludes uncited allegations** (even about the same resource/site) and returns no presumed registered origin or lawful owner. A firsthand sighting may establish the referenced physical action, but not absence of permission, guilt or enforceable title. The method must never become a public or character-facing source of omniscient knowledge; no new authentication boundary was installed.

New code commit `80c6e8cda04b8bc3219c59fe73e228e540523ce9`, four regression tests commit `7730f49b7908769ad1d0c150d565ca6376f56aab`: multi-witness and referenced claims (with unrelated false accusation), unseen action, unknown IDs, immutable snapshots/full replay. **Await exact-commit GitHub Actions to mark passing**.

**Stage scope still OPEN:** legal jurisdiction, formal right creation and contested-title resolution require approved prospective normative rules. No court, ruling, sanction, world migration or production authorization has been added.
