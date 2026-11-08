# PLAY-29 — final calibration report (2026-11-08)

**Decision:** `CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER`, experimental disposable-world scope only. **NOT** a finding that the village survives indefinitely. Schema **39** / Rules **51**.

## Scope delivered
1. Read-only seven-NPC food/hunger audit without hidden resource mutation.
2. Optional, immutable world-bootstrap hunger clock: 1 point per 3,600 logical seconds rather than the legacy 300; opt-out preserves legacy rules.
3. Optional, immutable lower action-hunger multiplier of 20%; action fatigue and labor remain real; opt-out stays 100%.
4. A/B tests, 7-day seven-character stress observations, historical fail-closed and deterministic SQLite replay.

## Technical evidence
- Source `1a4a4021367c670781eea5dee030fe9d93e65f37`; full [CI 42476104910](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42476104910) SUCCESS **1,670/1,670 tests per Python 3.10/3.13**.
- Comparative source `e3d023aa077db3fc544fc6a4271a7575140f4cd7`; [72h A/B CI 42475946942](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42475946942) SUCCESS both versions: starvation cap 7→0 at 72h with reduced action surcharge.
- Full-week test source `d67fefc09dddb17175e3799492167e4d4b03196c`; [CI 42476455377](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42476455377) SUCCESS on both versions. **All 7/7 NPCs hit hunger 100 by day 7** after finite personal rations exhaust. Seven days do **not** certify subsistence.

See [acceptance gate](PLAY_29_ACCEPTANCE_GATE.md) for each day's observed outputs and resource ledger.

## Handoff
Next stage must solve the physical food production and ownership/access bottlenecks without changing historic worlds. Start with independently justified crop/land/yield rules and test water, seed, worker, courier, distribution and deficit outcomes. No implicit rainfall and no auto-generated food. Maintain strict world versioning and source-of-truth events. `main` is untouched. P0 production safety and independent external review remain outstanding.
