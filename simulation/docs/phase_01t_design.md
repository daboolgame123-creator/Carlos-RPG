# Phase 01-T — Preliminary design: per-NPC knowledge of food-source locations

**Status:** design reviewed and **conditionally approved by the user (2026-11-04)**; three required revisions incorporated below. **No 01-T code has been written.** Coding must not start until this design is re-confirmed.
**Branch:** `simulation-engine-phase-01t`, based on `c35245d` (last approved, closed Phase 01-S; Schema 13 / Rules 17, 481/481 tests, CI success).
**Scope source:** [ROADMAP.md](ROADMAP.md) row 01-T, [DEVELOPMENT_PROTOCOL.md](DEVELOPMENT_PROTOCOL.md) §B/§C/§E, [architecture.md](architecture.md), [SAVE_COMPATIBILITY_POLICY.md](SAVE_COMPATIBILITY_POLICY.md), [phase_01s_report.md](phase_01s_report.md) OBS-1…OBS-5.

---

## 1. Decisions approved (decision log)

| # | Decision | Source |
|---|---|---|
| D1 | **Option A**: reuse `npcs[*].beliefs` with namespaced keys `food:<site_id>`; **Schema stays 13**; **Rules 17 → 18**. | User approval, conditional on contract integrity |
| D2 | Autonomous but **bounded information sharing** is in scope (coordinator-emitted delivery+ack under `knowledge_enabled`). | User approval |
| D3 | Confidence/staleness numbers are **experimental constants** (named, unit-tested, reviewable), not canon. | User approval |
| D4 | **Age separation (revision 1):** observation time and arrival time are distinct; re-sharing never refreshes the information age. Compatible with the current `claim` shape — see §4. | User requirement 1 |
| D5 | **Contradiction rules (revision 2):** explicit adoption/precedence rules for successive observations, fresh-hearsay vs old observation, and empty-then-regenerated sources; no observation is permanent truth. See §6. | User requirement 2 |
| D6 | **Source verification (revision 3):** direct-observation claims are verified in the reducer against actor location **and the real initialized resource balance at event time**; hearsay is never verified against world truth and stays a belief. No path allows a forged direct observation. See §5. | User requirement 3 |
| D7 | **OBS-2:** no new waiting introduced by the knowledge feature; acquisition/sharing never consume the 60 s decision slot. See §7. | Review obligation |

## 2. Baseline facts (verified, existing)

- `NPCInformationDelivered` / `NPCBeliefReceived` (01-C) already enforce: sender/recipient real actors, **shared recorded location**, no traveler on either side, `claim.received_at == state.time`, `method=message` ⇒ `claim.source == sender`, `method=observation` ⇒ sender == recipient and `claim.source == "observation:"+location`, one-shot ack consuming the inbox entry, unique `delivery_id` against `delivery_history` (`npc.py:89-125`).
- Claim shape is locked: exactly `{text, source, received_at, confidence}`; `text`/`source` non-empty strings; `confidence` integer 0–100; `received_at` integer (`npc.py:27-33`).
- **No production emitter exists**: in `src/`, the delivery events appear only in reducer/gate code; all emitters are in tests. 01-T must add emission logic.
- `_observe` (01-F) stores occupants only, never resources. `choose_local_foraging` (01-S) reads `wild_food` at the actor's current site only; `foraging_attempts` records verified direct outcomes. Neither changes in 01-T.
- All mutating NPC events require an open session and `npc_authorized`; flags are trusted local conventions, not AuthN.

## 3. Knowledge representation (Option A)

- **Key:** `food:<site_id>` inside `npcs[id].beliefs` (any non-empty key is valid, `npc.py:45`), site must exist in `state.locations`.
- **Value:** the unchanged four-field `claim`. Content semantics live in `text` under a **new strict grammar** (parsed only for `food:` keys; legacy keys such as `danger` keep their old validation untouched):

```
food-state:<present|empty>; observed_at=<int>
```

  Parsed by exact anchored match; `observed_at` integer `0..2^63-1`; for food keys, `observed_at <= received_at` is enforced at delivery.
- **Unknown = absent key.** An uninitialized site (`wild_food` key missing) can never produce `present` or `empty`. Empty is a positive claim, never an absent one.
- **Why no Schema change:** the claim key set, NPC profile keys and all top-level collections are untouched; `text` was already an unconstrained string. Grammar validation is *interpretation* of existing fields ⇒ a **Rules** change (§8).

## 4. Revision 1 — age separation: `observed_at` vs `received_at`

| Field | Meaning | Used for |
|---|---|---|
| `received_at` | when **this claim object arrived at this NPC** (enforced `== state.time` at delivery; advances every hop) | transport-freshness validation only |
| `observed_at` (inside `text`) | when the underlying fact was **last directly observed**; copied **verbatim** through every re-share | **the only input to staleness** |

- **Effective confidence is computed from fact age only:** `age = state.time - observed_at` (pure integer function `effective_confidence(claim, now)` in `knowledge.py`). `received_at` is never an input.
- Re-sharing therefore **cannot make old information new**: a fact observed at t=100 and re-shared at t=1000 arrives with `received_at=1000` but is evaluated with age 900.
- Direct observation: `observed_at == received_at` at first adoption. Hearsay: `observed_at` ≤ all arrival times by event ordering; validated `observed_at <= received_at`.
- **Experimental constants (D3):** base confidence — observation 90, hearsay 60, re-share `min(60, sender_effective // 2)` (integer). Age tiers from `observed_at`: `≤600 → ×100%`, `≤1800 → ×60%`, `else ×30%` (`base * num // den`, integer math, no RNG, no wall clock).

## 5. Revision 3 — source verification at event time

### 5.1 Direct observation (`method="observation"`, key `food:*`) — verified truth-at-write

The reducer validates **all** of the following, for trusted low-level batches as well:

1. Existing 01-C rules: sender == recipient, `location_id` == recipient's current location == `claim.source` minus prefix, not traveling, `received_at == state.time`, **and for a direct food observation `observed_at == received_at == state.time`**, unique delivery ID.
2. **New:** key site == the observation location (you can only observe food where you stand).
3. **New — real balance check:** `state["resources"][site]["wild_food"]` must be **initialized** (`type is int`); claim `present` ⇒ actual `>= 1`; claim `empty` ⇒ actual `== 0`. Uninitialized ⇒ reject (unknown ≠ zero/empty).

Consequence: a forged direct-observation claim that contradicts the actual stock at the actual actor location **cannot enter the event log**, even through a trusted capability — the reducer, not the emitter, is the boundary. Deterministic bonus: at a given tick and site exactly one truth value exists, so same-tick duplicate observation claims are necessarily identical.

### 5.2 Hearsay (`method="message"`, key `food:*`) — belief, possibly false

- `claim.source` must equal the immediate sender (existing rule); the sharing policy **always rewrites** `source` to the immediate teller and lowers confidence per hop. **New guard:** for `food:` keys, `method=message` rejects any `source` starting with `observation:` — hearsay can never masquerade as a direct sighting (including the theoretical NPC named `observation:<x>`).
- **Age is never refreshed by re-sharing:** `observed_at` is copied verbatim through every hop, so a fact observed at t=100 and re-shared at t=1000 arrives with `received_at=1000` but is still evaluated at age 900. Hearsay may therefore carry older information without renewing the observation date.
- **No truth verification** (architecture principle: delivery audits provenance, not truth): a false `present`/`empty` report about any site is *accepted* as a low-confidence belief, stays in the teller-attributed form, and never becomes a fact.
- The sharing policy reads only the **sender's own beliefs** — no remote `resources` access in emission.

### 5.3 Beliefs stay out of facts

No 01-T decision consumes food knowledge for action choice (§7); `known_food_sites(state, npc_id)` is a read-only recall API for 01-U. Poisoning remote stocks or foreign beliefs changes no decision event (adversarially tested).

## 6. Revision 2 — contradiction and memory-update rules

Adoption happens only in `NPCBeliefReceived` (ack consumes the delivery). The reducer applies the **same pure policy** the emitter consults: `should_adopt(existing, incoming, now) -> bool`.

| # | Existing | Incoming | Rule | Rationale |
|---|---|---|---|---|
| R1 | none | any valid | **adopt** | first knowledge |
| R2 | any | **observation** | adopt iff `incoming.observed_at >= existing.observed_at` (holds by event ordering) | a direct sighting never moves knowledge backward; covers successive observations and **empty → regenerated → present** |
| R3 | observation, age `≤ 1800` | hearsay | **reject** (keep existing belief; delivery consumed, no belief replacement) | recent direct sighting is protected; fresh news does not silently erase it |
| R4 | observation, age `> 1800` | hearsay | apply the **R5 comparison** (effective confidence, then larger `observed_at` wins) | protection lapsed: a stale sighting may be superseded only by genuinely newer/better hearsay |
| R5 | hearsay | hearsay | adopt iff `effective(incoming) > effective(existing)`; on equal effective, iff `incoming.observed_at > existing.observed_at` (larger `observed_at` = newer fact); otherwise **reject** (keep existing) | deterministic, field-only tie-break — no delivery IDs stored in claims |
| R6 | hearsay `empty`, recent | hearsay `present` | covered by R5 (age tiers decide) | regeneration via rumor only after the old direct `empty` loses effectiveness |
| R7 | any | observation | `incoming.observed_at >= existing.observed_at` required (holds by event ordering; mismatch ⇒ reject) | a direct sighting never moves knowledge backward |

- **Ack semantics:** an ack always **consumes the delivery** (removes it from the inbox). The belief is replaced **only if** `should_adopt` returns true; otherwise the existing belief is kept and no rollback occurs. Rollback (whole-batch rejection) is reserved for malformed or forged data that fails delivery validation. A rejected ack therefore never leaves a "pending" delivery — the delivery is consumed, the belief is unchanged. The emitter mirrors `should_adopt` before emitting, so autonomous flows never generate acks that the reducer would reject.
- **What is never done:** silent in-place mutation of beliefs outside an event, deletion of a claim without a superseding claim (history lives in the event log), or reinterpreting old `text` under new rules — the grammar is part of Rules 18 semantics.
- All rules are pure functions of `(claim, now)` ⇒ identical under snapshot/replay; OBS-1 provenance unchanged (event log + `verify()` remain the source of truth; `from_dict` stays consistency-only until P0).

## 7. OBS-2 guarantee — no new waiting

1. Acquisition triggers (arrival, forage outcome, explicit observe) and the sharing pass **never** emit `NPCDecisionRecorded`, never touch `next_decision_at`, never add to `busy`.
2. The sharing pass mirrors social gating (not busy, not traveling) and never `continue`-skips the NPC's forage/navigation evaluation; `local_forage_wins` ordering is untouched.
3. Sharing rate limits (`FOOD_SHARE_PAIR_COOLDOWN = 600` s per sender/recipient/site, at most one food delivery per pair per tick) are **sharing** limits, not decision delays — they cannot postpone a forage start.
4. There is no "wait until information expires" behavior in 01-T.
5. **Regression:** the OBS-2 scenario with `knowledge_enabled=True` reproduces 01-S timing exactly (forage starts at the scenario's decision cooldown), and a hungry NPC never spends more than the scenario's configured `decision_cooldown` (minimum 60 s) with no running action, no travel, and no due decision. The bound is the scenario's configured decision cooldown, **not a hardcoded 60 seconds**. Any fix beyond this bound and any memory-targeted travel belong to 01-U.

## 8. Schema / Rules / save / replay impact

| Item | Verdict (Option A, approved) |
|---|---|
| **Schema** | **13 unchanged** — no new collection, no profile/claim shape change; `from_dict` exact keys untouched |
| **Rules** | **17 → 18**, justified by §E: (a) food-claim grammar, (b) observation site-pinning + real-balance verification at event time, (c) adoption precedence — sequences valid under 17 become invalid under 18 |
| **Fail-closed matrix** | 01-T rejects `13/17` (01-S worlds) **and** `12/16` (01-R) via `UnsupportedVersion`, rows untouched; 01-S binaries reject `13/18` worlds on the rules mismatch. No migration (SAVE_COMPATIBILITY_POLICY) |
| **CI additions** | new step builds a **real 13/17 DB with 01-S code** and asserts rejection + unchanged rows (pattern of the existing 01-R step) |
| **Parity bench** | **no strip-list change**: `rules_version` is already stripped; flag-off ⇒ zero new events ⇒ `events_digest`/`legacy_semantic_digest` identical to 01-S |
| **Replay** | `NPCDecisionRecorded` re-derivation byte-identical (no decision changes); new belief events validated in reducers; `verify()` unaffected |
| **Flag** | `knowledge_enabled: bool = False` on `LivingWorldEngine`; disabled ⇒ legacy digests preserved (protocol §C) |
| **P0** | remains open; OBS-1 (`from_dict` consistency-only) unchanged, still a P0/05-D item |

## 9. Implementation plan (ordered, after design sign-off)

1. **`knowledge.py` (new):** grammar encode/parse (`FOOD_CLAIM_RE`), `validate_food_claim`, `effective_confidence`, `should_adopt`, `known_food_sites`, `choose_food_sharing` (pure; all constants named at top), emission helpers returning `(delivery_event, ack_event)` with deterministic unique IDs (`food-obs:{npc}:{site}:{time}:{trigger}`, `food-share:{sender}:{recipient}:{site}:{time}`; collision-checked against `delivery_history`).
2. **`npc.py`:** food-key branches in `NPCInformationDelivered` (site pinning, initialized-balance verification, `observed_at <= received_at`, `observation:`-prefix guard for messages) and `NPCBeliefReceived` (grammar parse + `should_adopt`). No legacy-key or decision-validation edits.
3. **`living_world.py`:** `knowledge_enabled` flag (default False, boolean check); arrival hook after `__npc_travel_id` firing; forage-outcome hook after `resolve_foraging`; sharing pass in deterministic NPC-ID order, bounded, event-budget aware.
4. **`movement.py`:** explicit `observe` routed through the same acquisition helper.
5. **`domain.py`:** `RULES_VERSION = 18` only.
6. **`store.py`:** no expected change (existing `npc_authorized` gate covers the new events).
7. **Tests:** §10 files; **CI:** 13/17 real-DB rejection step; parity step unchanged.
8. **Docs at closure:** phase card (§B), architecture.md section, ROADMAP status, report with §C evidence.

## 10. Test plan (~48–55 tests)

### 10.1 Unit — `test_knowledge.py` (~14)
Grammar accept/reject matrix (missing/extra tokens, bad enums, out-of-range `observed_at`, `observed_at > received_at`); `effective_confidence` tiers (0/600/601/1800/1801, base 0/90/100, integer rounding); `should_adopt` full matrix (R1–R7) asserting **emitter decision == reducer acceptance** for every (existing × incoming) pair; `known_food_sites` reads only the named NPC's beliefs; sharing determinism (order, IDs, cooldowns); unknown ≠ empty.

### 10.2 Adversarial — `test_knowledge_adversarial.py` (~17, incl. the requested new cases)
Common pattern: `before = db.load(w).to_dict()` → attempt → expected exception → `after == before` + events-row count unchanged.

**Forged direct observation (D6):**
1. `test_forged_observation_wrong_location_rejected` — claim.source/`location_id` ≠ actor's current site.
2. `test_forged_observation_present_when_stock_is_zero_rejected` — reducer balance check.
3. `test_forged_observation_empty_when_stock_positive_rejected` — mirror case.
4. `test_observation_on_uninitialized_site_rejected` — unknown cannot become `empty`.
5. `test_forged_observation_from_traveler_or_wrong_time_rejected` — existing 01-C gates re-proven for food keys.
6. `test_hearsay_cannot_masquerade_as_observation` — `method=message` with `source="observation:*"` rejected; also non-food legacy behavior untouched (regression).

**Age separation (D4):**
7. `test_hearsay_arrival_does_not_refresh_age` — fact at t=100, re-shared at t=1000 ⇒ `received_at=1000`, `observed_at=100`, effective confidence equals age-900 value, **not** a fresh claim.
8. `test_double_reshare_preserves_observed_at_and_drops_confidence` — chain of two hops; age unchanged, confidence halved per hop (bounded).
9. Parametrized: re-share at ages just below/above each tier boundary — deterministic integers.

**Contradiction rules (D5):**
10. `test_successive_observations_latest_wins` — `present@t1 → empty@t2 → present@t3` (regeneration); final claim carries `observed_at=t3`.
11. `test_fresh_hearsay_cannot_overwrite_recent_observation` — ack rejected, state unchanged, delivery stays pending.
12. `test_stale_observation_superseded_by_hearsay` — same pair after `>1800` ⇒ adopted (R4).
13. `test_hearsay_vs_hearsay_fresher_fact_wins_and_tie_keeps_existing` — R5 including exact-tie keep.
14. `test_old_observation_is_not_permanent_truth` — no observation claim outlives the authoritative window against contradicting evidence.

**Belief-not-fact (D6) + knowledge boundary:**
15. `test_false_hearsay_is_accepted_as_belief_not_truth` — wrong `present` report accepted (source=teller, confidence ≤60) yet no decision or reducer treats it as a fact; decisions unchanged.
16. `test_planner_invariant_to_remote_stock_and_foreign_beliefs` — poison `resources[remote]`, others' beliefs ⇒ `choose_action` byte-identical.
17. `test_knowledge_in_from_dict_detected_by_verify` — OBS-1 pattern: consistency-only `from_dict`, `verify()` still flags a tampered DB.

Plus existing-pattern guards: capability/session gates for the new events, batch atomicity with one bad knowledge event, duplicate delivery IDs.

### 10.3 Integration — `test_knowledge_scenario.py` (~7)
Seven-NPC lifecycle: observe → remember → hearsay → reconfirm → stale → empty → regeneration across ≥4 cooldowns; `verify()`/snapshot/reopen/rerun hash equality; session-close and event-budget rollback mid-lifecycle; per-NPC independence (one hears, co-located peer unchanged, decisions diverge only via knowledge, equalize ⇒ equal decisions); **OBS-2 pair:** identical forage timing flag on/off + `next_decision_at` never moved by knowledge emissions + ≤60 s bounded-idleness invariant.

### 10.4 Compatibility (~5)
Flag-off digest parity vs 01-S (all three digest keys); real `13/17` and `12/16` DB rejection with rows untouched; parity-bench strip-list confirmation (no change expected); compileall; Python 3.10/3.13 in CI.

**Estimated totals:** unit 14 · adversarial 17 · integration 7 · compatibility 5 → **≈43 core + parametrized bounds ≈ 48–55**.

## 11. Risks and remaining open items (with defaults)

1. **Constants are experimental** (90/60, 600/1800 tiers, 600 share-cooldown) — named, unit-tested, adjustable without re-baselining behavior.
2. **Rejected-ack pending deliveries** linger until adoptable — bounded by inbox/history and re-evaluated under the event budget; if review dislikes lingering, alternative is adopt-without-overwrite, which needs a payload change (Rules-visible) — default: keep rejection.
3. **Sharing volume vs event budget** — one delivery per pair per tick + per-site cooldown keeps advance batches small; rollback-on-budget is existing semantics.
4. **Grammar-in-`text`** trades a structured field for zero Schema churn — strict anchored parsing mitigates ambiguity; upgrading to Option B (Schema 14 projection) stays available for 01-U/01-V if quantity/history needs appear.
5. **Hearsay can inject false `present`** about a site — accepted by design (belief, low confidence, no decision impact in 01-T); rumor *truth-testing* belongs to 02-G.
6. **Share-cooldown persistence:** per-pair cooldown IDs are derived deterministically from `(sender, recipient, site, time)` and checked against the durable `delivery_history`, so the sharing limit survives SQLite close/reopen with no new state collection.

## 12. Explicitly out of scope

Travel/navigation toward remembered sources (01-U); fairness, scarcity, regrowth (01-V, 02-A); stored quantity claims and per-site history; multi-hop rumor chains/original-source tracking (02-G); any change to `choose_local_foraging`, decision cooldowns, `local_forage_wins` or base utility; Carlos story/`main` changes; migration of any old world; P0 closure itself.

---

**STOP marker:** this document is the reviewable design artifact. **No implementation code, test code, or engine change may be written until the user re-confirms after this revised design.**
