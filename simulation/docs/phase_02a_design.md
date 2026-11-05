# Phase 02-A — Finite, conditional environmental replenishment (first slice)

**Baseline:** reviewed-by-CI Phase 01-Z commit `1225ae066f22bc2688a583d46e63ceda80558a07`, [Actions 42060397577](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42060397577), 643 passed on Python 3.10 and 3.13.
**Branch:** `simulation-engine-phase-02a`; **status IN_PROGRESS**. P0 OPEN, external independent review deferred. All fixtures disposable.

## Scope and invariant
01-Q/01-S physical gathering already consumes finite, visible site `wild_food`. Phase 02-A introduces one explicit **resource-conserving** environmental conversion policy, not an invented endless growing resource: a particular site has two known initialized stocks, `wild_food` and `regrowth_reserve`. At a user-configured, finite period, the engine converts **at most one unit** of `regrowth_reserve` into one `wild_food`, only if `wild_food < capacity` and the reserve is positive. If the reserve is zero, the site stays empty; if the food deposit is full, no reserve is wasted. **Total food+reserve is conserved on each renewal**, before NPC gathering/consumption. A deliberate initial reserve is the cause of new harvestable food, not an infinite or remote supply.

- Trusted world bootstrap event `EnvironmentalCycleConfigured` at logical time 0 only: `{id,site_id,period_seconds,capacity}`; site must exist and BOTH balances must be initialized, known, nonnegative. No autonomous creation of initial resources. One cycle per site.
- The same event creates a deterministic, non-interrupting scheduled appointment with explicit `__environment_cycle` provenance. Only trusted clock `ScheduledEventFired` can perform the transfer; the projection schedules the following appointment **only if reserve remains** (including after a capacity-full no-op). The source and target, interval and capacity remain fixed; a malicious generic `ScheduledEventCreated` cannot introduce an environment appointment, nor can generic `ScheduledEventCancelled` delete it. No new network/RPC capability.
- The existing `TimeEngine` and opt-in `LivingWorldEngine` both execute scheduled appointments, so the first slice operates without an additional NPC planning flag. However it is **opt-in via trusted bootstrap configuration**: unconfigured worlds behave exactly as 01-Z, with no new NPC knowledge of distant stocks. No NPC automatically learns an unseen site has replenished food.
- `environment_cycles` is an immutable, validated state collection, storing period/capacity, fired count and converted total, previous/next due time, and the site. The sole source of truth is the configured event plus replay of clock firing events, never the current external wall clock or a mutable snapshot.
- The existing `wild_food` gathering behavior remains unchanged; characters still need local presence, a completed real action and sufficient stock to take food. No new growth without finite reserve. Seasons/weather/crops, true biomass creation, farming recipes, markets, ownership and ecosystem replenishment of the reserve are deferred.

## Compatibility and acceptance
New snapshot field plus event interpretation require **Schema 15 / Rules 22**, compared with 01-Z 14/21; no migration. Real SQLite world made by 01-Z must be refused unchanged. Keep frozen 7-NPC event and semantic parity (exclude only genuinely new empty `environment_cycles` in legacy semantic comparison; retain full audit hashes). Verify:
- opt-in only, known vs missing resource, capacity and reserve limits, exact 1:1 conversion, deterministic duration and split time, zero-resource exhaustion and no creation when full;
- multiple sites compete neither for each other's stocks nor knowledge; NPC gathering/food consumption retains conservation and timings;
- stale/duplicate commands, denied forged config/schedule/cancel events, early/out-of-order scheduled firing and session shutdown, malformed snapshot, batch rollback and replay integrity;
- SQLite snapshot/reopen, 01-Z backup/restore, Python 3.10 and 3.13, full prior CI and genuine predecessor version refusal.
- P0 remains OPEN and independent review DEFERRED; no long-lived/canon save, HTTP exposure or story import.

**Caveat:** The name `regrowth_reserve` is a pre-provisioned environmental **potential budget**, not literal seed nutrition. Converting it consumes actual test-world units. Any realistic physical biological regeneration must later have explicitly accepted ecology/energy/seasonal rules and cannot silently override this finite contract.
