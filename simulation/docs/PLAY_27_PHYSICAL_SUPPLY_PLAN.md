# PLAY-27 — finite well water and real road-borne cargo logistics

**Plan status:** OPEN / IMPLEMENTATION_PENDING (2026-11-08).
**From:** PLAY-26 docs commit `0283df637360a566a572a54dd051cd416fecd981`; branch `simulation-engine-phase-play-27-physical-supply`; never edit `main` or canonical Carlos story.
**Prior:** PLAY-26 proved two seeded cycles at a *single shared test site*, not goods movement or full-survival endurance.

## 1. Scope: three real, non-teleporting physical supply legs

A seven-NPC test world uses locations `well`, `farm`, `bakery`, `market`, `home`, linked by actual existing routes with positive travel time. Huda the courier follows an explicitly registered, deterministic six-leg circuit from her *professional route assignment*: `well→farm→bakery→market→bakery→farm→well`, at most once every six logical hours. The circuit is finite, rate-limited and not a source of remote resource knowledge. Adjacent route IDs and positive transit durations must be validated at bootstrap.

**Three one-unit local cargo operations:** carry `water` from the well to farm; `grain` from farm to bakery; `food` from bakery to market. Pickup debits the **actual source-site inventory**, credits **Huda's personal cargo ledger**; delivery debits only the personal cargo ledger and credits the **actual adjacent destination-site inventory**. No goods pass from site to site without a traveling carrier, no double loading, invented remote stock, teleportation, or negative balances. Stops with zero local supply simply move on. Circuit phase advances only at physically completed trips; the real movement reducer and its scheduled due time remain authoritative.

The farm can plant only with delivered water and finite seed; the baker can produce only with delivered grain and oven; Salma can offer only food physically delivered to market. All old modes default off. This requires new durable `supply_circuits` world state, explicit `SupplyCircuitConfigured` bootstrap, `SupplyCargoPicked` and `SupplyCargoDelivered` runtime events with a separate persisted `supply_authorized` capability; version must bump Schema 35→36 / Rules 47→48 and update pinned current-world test expectations without rewriting historical predecessor expectations. Frozen feature-off probes must assert empty circuits before omitting the empty new field for cross-version semantic comparisons.

## 2. Endurance and honest scope

Run five disposable seven-person counterfactuals through **3+ logical days**: full finite source with 2 well water units, one well unit, no well water, no seed, missing courier. No completed grain/food/trade before physical carriage. At least two seeded harvests and two bakes when funded and courier active; zero mass/note creation. Track whole-world crop seed, water, grain/food equivalents including producer reservations, consumption and courier loads, and currency; verify byte-exact replay and SQLite snapshot/reopen.

A second limited **full metabolism** branch (`survival_enabled=True`, seven NPC, over multiple days) deliberately permits hunger/fatigue to rise and can fail to sustain the village. It must truthfully report any production collapse: existing model cannot yet simulate starvation death, complete rest, wages, rainfall or all everyday actions cheaply for several days. Do not label a focused economic test a full-life test. Keep both scenarios explicit.

## 3. Gates

- Before code: committed analysis. Then write strict reducer + deterministic planner + physical scenarios/tests with appropriate trust/capability guards.
- Python 3.10 and 3.13 targeted CI plus genuine complete regression, including older branch parity. Both must pass on the **same tested code SHA**, all historical parity steps included.
- Document-only close in `ROADMAP.md`, `WORK_QUEUE.md`, plan and final report **after** two green workflows; otherwise leave stage open with precise blocker. No premature P0/production authorization; external review remains deferred.
