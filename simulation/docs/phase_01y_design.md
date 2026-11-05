# Phase 01-Y — Minimal opt-in player RPG state, not RPG mechanics

**Baseline:** Phase 01-X `b1f1c265a09d23cef3a1078cee98e3952a37ab39` — CI [42034258102](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42034258102), 615/615 on Python 3.10 and 3.13.
**Branch:** `simulation-engine-phase-01y`. **Status: IN_PROGRESS** until full CI. **P0 OPEN**; **EXTERNAL_REVIEW_DEFERRED**; no story import or long-term save.

## Gap and design
The trusted player gateway already moves, observes, interacts and remembers, but there is no RPG status projection. We need a safe shape for health/stamina/mana, experience, level, attributes, inventory and equipment without pretending the engine has combat or XP rules.

An unconfigured player has **no RPG record**; `status()` returns `rpg_uninitialized`. Initializing a profile is an explicit `PlayerRPGInitialized` trusted bootstrap event at logical time 0, after creating the player entity. It contains all of:
- `vitals: {hp:{current,max}, st:{current,max}, mp:{current,max}}`, where either unknown `None` or a nonnegative integer not exceeding a known maximum; unknown is never coerced to zero.
- `xp_current`, `xp_goal`, `level` and `attributes`, all nullable/explicit: no guessed XP threshold, level-up rule or attributes. Integers/identifiers are bounded.
- `inventory: {}` and `equipment: {}` only. **Ownership/acquisition/equip rules do not exist**, so populated inventory/equipment are rejected even at bootstrap instead of minting imaginary items.

`PlayerVitalChanged` supports bounded, explicit test-only adjustments to previously known HP/ST/MP with `previous`, `current`, `source="test-scenario"`, and cause/time/event provenance. It requires a distinct *trusted* `rpg_authorized` capability and active session; cannot be issued through the player gateway. There is **no automatic healing, mana recovery, exhaustion, damage, XP gain, leveling, equip or inventory transfer**, and no generic "set any RPG field" endpoint. These require later explicit rule designs and event evidence.

## Trust, version, save
- `PlayerGateway.status()` sends only the invoking player profile as a **detached** JSON-like object. An NPC profile, another player's RPG data, world resources and hidden beliefs never cross this boundary.
- Event reducers and `WorldState.from_dict` validate the same strict profile contract, including replay and snapshots. The SQLite command table stores the separate `rpg_authorized` provenance flag for re-verification after reopen. Arbitrary event or player commands cannot bypass the flag.
- Schema **13 → 14** (new optional `WorldState.rpg_profiles` map and command provenance column); Rules **20 → 21** (new event types and rules). Existing 13/20 worlds must be rejected unchanged, without migration. Tests use **disposable** worlds. No original Carlos narrative state is imported, and no old worlds are silently upgraded.
- The temporary CLI fixture contains **fictional sample HP 12/12, ST 8/8, unknown MP/XP/level** solely for demonstrating `status`. These are not historical Carlos facts. CLI does not offer status editing.

## Acceptance
Test opt-in/unknown, own-profile-only access, malformed/negative/oversized stats, fake items/equipment, NPC impersonation, missing capability, closed session, repeat/stale command, forged previous value, maximum boundaries, failed batch atomicity, snapshot/reopen/full replay and real predecessor 13/20 rejection. Cross-version NPC event and semantics probes must not change; only version and genuinely new empty opt-in RPG collection are excluded from frozen semantic digest, with full digests retained.

**Not included:** actual HP/ST/MP game rules, level-up, XP awards, attribute growth, equipment, item ownership/transactions, original story import, migration, permanent saves, network AuthN/AuthZ or independent review.
