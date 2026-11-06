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


## Proposed local-title law contract — guarded draft only (2026-11-06)

After verifying **932/932 full regressions on each Python 3.10 and 3.13** at code commit `7730f49b7908769ad1d0c150d565ca6376f56aab` ([CI 42225392959](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42225392959)), the next scoped step was to create a **non-binding prospective local-law draft validator**, not a jurisdiction or legal-title engine.

### Explicit decisions in this provisional contract

1. A proposed law applies to **one existing location**, with **simulated effective time strictly in the future** (no retrospective change).
2. Possible authority models for later political design are `customary_assembly`, `local_council`, or `lordly_authority`. The string is **a proposal, never a credential or installed institution**.
3. The only supported draft transfer condition is `requires_preexisting_verified_title_and_mutual_consent`. Bare possession, a sale receipt or a registered historical claim cannot establish an enforceable legal title.
4. Four explicit prerequisites remain unmet: approve institution/scope; verify prior title; identify goods and conflict procedure; implement audited versioned event authorization/replay. The function returns `review_status="unapproved_draft"`, `jurisdiction_effective=False`, `authorized_institution_id=None` and `legally_enforceable_owner=None`.
5. No legal event, court, title ledger or migration is added. Schema 28 / Rules 36 remain unchanged; the draft is intentionally **off-ledger**, has no effect on an NPC or the world's resources, and is restricted to trusted internal design evaluation.

**Implementation:** `simulation/src/carlos_sim/title_law_draft.py` (commit `383ca096a85dee498f3294ddc5328b98411931a0`). **Tests:** `simulation/tests/test_title_law_draft_04a_j1c2b.py` (commit `ab7a5a00afe3b38fbb75aa07caa740a4f2b4b006`) verify valid proposals remain powerless; invalid sites/authorities/retroactive and boolean times/possession-based title fail closed; proposed authority grants no privileges; logical time and replay/snapshot invariants.

**Status:** Implementation complete as a **non-binding draft validation slice**, CI pending on the new exact code SHA. This does NOT select a political ruler, establish enforceable law or close J1c2b. The later choice of normative institution/title provenance remains explicit and separately testable. Independent review deferred by owner, production P0 and network authorization remain unapproved as tracked in `EXTERNAL_VALIDATION_LEDGER.md`.


## Institution charter nominee validation — nonbinding and off-ledger (2026-11-06)

The latest full regression checks for code commit `ab7a5a00afe3b38fbb75aa07caa740a4f2b4b006` completed SUCCESS: **950/950 tests on each Python 3.10/3.13**, plus companion adversarial jobs ([full CI 42226560154](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42226560154)).

Next scoped change adds `prepare_local_institution_charter_draft` as an **unapproved institution nomination validator** next to the existing local law draft. It requires a real existing site, a real local non-traveling and not-currently-occupied NPC nominee, a syntactically valid institution ID, an enumerated proposed institutional model and a strictly prospective effective time. This leverages the existing `market._present` physical presence rules on a detached world-state copy.

It explicitly reports `nominee_consent_recorded=False`, `institution_registered=False`, `appointed_officer_id=None`, and `can_decide_title=False`, `can_seize_property=False`, `can_delegate_authority=False`. The *proposal string* **is not a capability**, and there is no event, persistent institution ledger, authentication, law registration or jurisdiction. It does not grant a complaint-desk officer judicial powers.

Source commit `5d42031d8c60cbf6b4a1ad67ad70eff80477b7e4`; tests commit `2eab41472acc4d8c284872b879be119931d7021c` covers detached no-side-effects, invalid nomination/site/model/time, traveling nominee and replay consistency. **New code still requires exact-commit CI success** before test claims can be made. This is a technical prerequisite, **not** a binding title engine or a J1c2b closure.

Open design prerequisites: record nominee's explicit consent, establish an actual institution jurisdiction and powers by approved world rules, develop trusted registration event provenance and authorize future civil procedures. No explicit world-political authority has yet been selected. Production P0 and external independent review statuses remain tracked separately in `EXTERNAL_VALIDATION_LEDGER.md`.


## First persisted local institution founding record — implementation under verification (2026-11-06)

Following 962/962 verified full regressions each on Python 3.10/3.13 for the off-ledger nominee design ([CI 42227263627](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42227263627)), we added a **narrow persisted founding record**.

- **DomainEvent:** `LocalInstitutionRegistered` accepted **only** with trusted `bootstrap=True`, simulation time zero and `actor_id=None`, with an existing site and available real co-located NPC representative. The registration is bounded (100) and refuses duplicate institution IDs, duplicate sites and repeated representatives. Event becomes independently replayable in SQLite like other trusted setup records; invalid events roll back atomically.
- **Stored collection:** `local_institutions` with `site_id`, `representative_id`, `model`, `registered_at=0`, and exact `mandate="existence_record_only"`. Full state validation rejects forged snapshot fields and fake representatives. The representative is a recorded **founding-site contact, not a judge**, and historical consent is **not** inferred from mere presence.
- **Schema 29 / Rules 37**, both deliberately bumped. Existing Schema28/Rules36 worlds must be rejected without mutation; no implicit migration. This is a breaking snapshot format change for disposable-world tests only.
- **No legal authority:** The event is not a law, title, court, complaint adjudication, right to confiscate, or assumption of political legitimacy. `institution_record` is trusted audit-only and explicitly `can_decide_title=False`, `can_seize_property=False`, `authorized_court_id=None`.
- **Implementation commits:** `ecd79f05c8c4a6f73d24dbcc6ce70a886f51671d` (new module), `9a20e76b48fd6b893d995c1f79a46fa2859d4a8a` (versioned Domain integration), `eccf90eef066ebc5d7ea303f9b5771eb41a38690` (tests).
- **Tests added** for successful physical founding, forged actor and fake/remote representative, absent trusted capability, duplicate site, mixed valid+invalid atomic rollback, forged snapshot, independent reopen and full replay, old schema rejection.

**IMPORTANT VALIDATION GATE:** These changes are **not yet technically accepted** until full and adversarial CI completes on the exact code SHA. A separate end-to-end old-world file byte-for-byte rejection is desirable in addition to the current old-format snapshot unit check; if not run, keep it as an unverified test requirement. An actual law, title registry and binding title-transfer rules are still unimplemented. J1c2b remains OPEN; independent review deferred and production P0 not approved.


## Follow-up integration review and CI remediation (2026-11-06)

- Initial Schema29/Rules37 run on code `eccf90eef066ebc5d7ea303f9b5771eb41a38690` **FAILED**. Adversarial recovery job identified a J1c2a test pinned to 28/36; full Python 3.10 suite yielded **958 passed, 17 failed**, all reported failures asserting old version numbers (not yet evidence that the new registry behavior was wrong).
- Updated the J1c2a recovery-manifest expectation to use `SCHEMA_VERSION/RULES_VERSION` at `d8397709d9b3a87bbccf2a301cf1518db92f5e1d`, and re-pinned version-only assertions in the 14 impacted legacy test modules to **29/37**. These changes do **not** relax fail-closed rejection of actual old-world state.
- Added SQLite old-version refusal test asserting bytes remain untouched after failed load (synthetic older-version row; **not** equivalent to running a genuine historical 28/36 file), commit `701c198264e6e5fde3966ad0dae98a07a1a27f38`.
- Extended the independent-process `j1c2a_offline_recovery_drill.py` to include a genuinely persisted `LocalInstitutionRegistered` record in the seven-NPC world; script explicitly verifies no court power pre-backup and after restore, commit `0652e639bc5b1df71fff29b39a872368392b118c`.
- Hardened malformed institution model-type rejection, commit `617b931da5cc3b433525ae6410f5e878dfc87012`. New exact-commit full regression, dedicated adversarial and standalone recovery CI on Python 3.10/3.13 were queued at documentation time. **Do not mark J1c2b validated until all required jobs succeed.**
- The external independent reviewer is deferred by owner. Production-specific P0 remains unapproved. This registered institution is a **founding existence record only**, with no authority to validate ownership, judge, seize, punish, or bind parties.


## Cross-version parity regression remediation — local evidence (2026-11-06)

The exact-commit full CI on `617b931da5cc3b433525ae6410f5e878dfc87012` (run `42229493643`) passed pytest (`976 passed`) but failed the Phase 01-T flag-off parity gate on `legacy_semantic_digest`.

**Root cause:** adding the empty `local_institutions` collection for Schema 29 changed the semantic-state projection used by cross-version parity benches. The strip lists in those benches enumerate every collection added after the frozen baseline, but `local_institutions` had not been added. A field-by-field comparison under genuine 01-S and current code confirmed:

- identical `events_digest` (`e4414d12…`) and event count (51);
- identical values for every shared semantic field;
- one additional key only, `local_institutions == {}`.

This is a test-projection omission, not a behavioral regression.

**Fix:** add `local_institutions` to the semantic projection of `bench_event_parity.py`, `bench_food_knowledge_parity.py`, and `bench_scarcity_disabled_parity.py`; extend `test_knowledge_compatibility.py` with a guard covering all three benches. No expected hash was replaced and no event-integrity or parity assertion was removed.

**Local verification (Windows, Python 3.13 and 3.10):** full suite `976 passed, 1 skipped` on each; 01-T digest restored to `7d2be0d6c63594aaf7d6aa60f03be97a9c01747a7606931c66b2cc91c710bdf9`; 01-U `e2fa8107…`, 01-V `ef830145…`, and 02-F/02-G/01-R parity checks all equal.

**Second stale expectation found by CI (`42244658986`):** pytest and the adversarial workflow passed, but the 01-U step failed because the workflow pinned the candidate to Rules 36 while the current rules version is 37. The candidate pins in the 01-U and 01-V steps are now 37 (baselines remain 18), with `test_ci_parity_gates_pin_current_rules_version` guarding future bumps. Exact-SHA GitHub Actions remains required before closure; this section does **not** claim J1c2b validated or independent review.
