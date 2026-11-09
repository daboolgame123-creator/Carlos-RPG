# Carlos RPG — approved acceleration plan (2026-11-09)
 
> **Owner decision:** use the refreshed model allowance to achieve substantial verified development, not merely to increase PLAY numbers. Priorities: autonomous NPCs and an economically alive world, then a playable observer/player experience. This is a forward plan, **not** evidence that later stages are implemented. This plan does not authorize skipping acceptance gates. Read `AGENTS.md`, `DEVELOPMENT_PROTOCOL.md` and the live GitHub state first.

## 0. Current checkpoint; never trust this section over live GitHub

- Repository: `daboolgame123-creator/Carlos-RPG`.
- PLAY-45 technically closed at `a6c20e3edfbe85cc68819cd4fadd909472b21fd5`; current PLAY-46 candidate: `feature/play46-multi-input-atomic-recipes-20261109`.
- At document creation, PLAY-46 feature HEAD was `6020b92c443042ea81ef76b6b637ae10961b4d02` with Schema **42**, Rules **57**, PR #40 still Draft. PR #41 had already been integrated into this feature branch. `main` was not merged.
- At document creation: PLAY-46 targeted CI [42613658371](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42613658371) **SUCCESS**. Historical full CI [42609660548](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42609660548) **SUCCESS** on the same SHA (1,694 tests per Python 3.10 and 3.13). A newer branch-triggered historical run [42613666694](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42613666694) was **in progress** at the last check: 3.13 completed successfully; 3.10 not yet confirmed. **Fetch its actual final result before making closure claims.**
- Before opening PLAY-47: verify exact-feature-HEAD targeted and historical CI on both Pythons, replay and authentic v41/56 predecessor refusal, review the autonomous route/procurement tests, update closure evidence and `WORK_QUEUE.md`. External review deferred by owner and P0 production approval **are not** technical approval or permission to run public services or durable worlds.

## 1. Goal and order

Deliver a *world-first* realistic medieval economy. NPCs work, buy, travel, fail, eat, receive real funded wages and respond to shortage **without Carlos directing the system**. Copper never appears spontaneously; finite materials have provenance; markets are physically staffed and located; NPC decisions obey their own knowledge, existing roads and time. SQLite event history is the source of truth; ChatGPT/OpenCode models explain and interact, not authorize or invent state changes.

**Gate order**: finish PLAY-46 → PLAY-47 → PLAY-48 → PLAY-49 → PLAY-50 → PLAY-51. These numbers are proposed planning slots and should be confirmed in the roadmap when they open. A successor stage that depends on a blocked stage MUST NOT begin; unrelated safe validation/docs may continue.

### PLAY-47 — Multi-day NPC economic endurance (highest priority)

Tasks in a single measured batch, provided dependencies pass:
1. **47-A — scenario contract:** 7–10 realistic NPCs, distinct workshops/shops, roads, finite wallets, production and hunger. Record expected resources and location knowledge at t=0; no hidden free replenishment.
2. **47-B — ledger audit:** time-series of copper by owner, market purchases, inventory by owner/location, wage settlement, completed/unpaid work, jobs pending, travel success/failure and shortages.
3. **47-C — 24h / 72h / 7d trials:** grow horizon only as earlier scenarios meet invariants. Use naturally autonomous NPC behavior, not scripted NPC shopping.
4. **47-D — isolate failures:** identify root cause separately as liquidity, supply, production rate, wage financing, travel/network knowledge, fatigue, food, tool scarcity or deadlock. Reproduce before patching.
5. **47-E — minimal fixes:** only repairs supported by evidence; no minting stock, teleports or gift wages to make dashboard green.
6. **47-F — acceptance:** replay/snapshot/SQLite verification, time-partition invariance, duplicates/unauthorized commands, no global market omniscience, default-off parity, exact-head full CI 3.10/3.13, concise evidence report.

Measure: starvation profiles, workforce activity, fair trade opportunity, completed jobs, genuinely paid/unpaid wages, cash distribution, total conserved copper and market stock. Economic collapse due to actual shortage can be a **valid observed outcome**; do not falsely label it sustained.

### PLAY-48 — Repeatable physical production and liquidity loops

- Use existing **wood → carpenter → builder** and **ore + charcoal → smith → repairer** chains. Confirm bounded real resource origin, local transfers, multiple iterations, authentic consumption of compound recipe inputs, tool use and time.
- Treat resource depletion, stalls without staff, insufficient buyer cash, unsold goods, missing tools and insolvent employers as legitimate failures.
- Add only the minimum extraction/charcoal/replenishment mechanism whose provenance and rates can be audited. Never silently introduce renewable supply or make tool repair free.
- Gate: two or more full causal loops **if resources actually permit**, conserved money, no negative/duplicated stock, one funded wage per legitimate job, exact replay and adversarial checks.

### PLAY-49 — Distinct markets and lived demand

- Incrementally evaluate a fruit/vegetable retailer, dairy/cheese shop, then tavern (not all at once).
- Every added seller must have its own genuine source, finite stock, ownership, time-based labor, local physical trade, buyers with relevant needs and budget, and optional spoilage only with proven expiration rules.
- The tavern must consume inputs and pay from existing revenue, not grant free meals, goods, wages or lodgings. If supply chain is not feasible, record the blocker and stop.

### PLAY-50 — Builder path with world consequences

- Create a bounded **wooden house construction** scenario: site, materials, worker skills, physical delivery, tool capacity, time-based construction progress, paid or explicit unpaid labor, and stable construction receipts.
- Integrate Carlos's planned builder route as **player-initiated** actions; NPC economy remains independent. The earlier 35% progress/18 of 20 wood mockup is illustrative, not a world-state claim.
- Do not add magic or impossible instant construction. Optional future mana-assisted cognitive/material abilities require separate contracts, cost, balance and owner approval.

### PLAY-51 — Trade between villages, not two isolated test worlds

- Only after local chains work. Two distinct settlements with independent real goods, routes, markets, scarcity and cash; couriers or traders must travel and deliver stock physically.
- Verify ownership transitions, cross-village transaction ledgers, delayed delivery, route failure, shortage/insolvency, event replay and **global** cash/material provenance.

## 2. Execution strategy and staffing

- Plan by **batches of 3–8 small tasks** (reduce if critical dependencies require), with one root-cause analysis and acceptance criteria for each related subtask. Do not stop after one small fix just to ask to continue.
- Primary lead is **ChatGPT in this conversation**; use GitHub/GitHub Actions deterministically. Send a tightly-scoped task to **OpenCode only when its environment, local scripts, parallel coding or an external verifier is genuinely useful**, not by default.
- When a delegated task exists, log `ChatGPT working on ... / OpenCode working on ...`, branch, expected files, ownership, SHA and CI. Avoid simultaneous edits to the same branch/path.
- Unit/targeted suites during work; **full historical CI once per final candidate** after necessary fixes rather than once per edit. Verify latest SHA on both Python 3.10 and 3.13; a green check on an earlier commit is not sufficient.
- Before any Schema/Rules change: evaluate old saves, rollback/backup, explicit fail-closed refusal and test-only migration policy. No `main` merge or public/auth-untrusted network/API until the owner's specific production and review gates are satisfied.
- Distinguish `CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER` from external approval. Record `BLOCKED` and real remaining failures.
- Use [model routing inventory](OPENCODE_AVAILABLE_MODELS_2026-11-09.md) for OpenCode; choices are **candidate assignments**, not unverified rankings. Spend higher effort only on root causes, integrity/replay and hard architectural decisions; use tests for factual validation.

## 3. Outcome objectives for the next model allowance

- **Mandatory:** finish and document PLAY-46's exact-feature-HEAD CI and technical closure, or report genuine blockers.
- **Primary stretch:** design, implement, test and technically close PLAY-47 if gates are met.
- **Second stretch:** deliver PLAY-48's repeatable production loops with test evidence and closure where possible.
- **Conditional:** open PLAY-49 only after 47/48 gates; preserve scope rather than claim false speed. Keep a separate playable observer/builder vertical slice visible in the backlog.
- Report only confirmed outcomes: last branch, complete SHA, Schema/Rules, number of tests, actual CI links, test scenario and remaining gates. No invented simulation results, tests or background execution.

See [new-chat handoff](CARLOS_NEXT_CHAT_HANDOFF.md) for the minimal startup checklist.
