# OpenCode transfer — Carlos Simulation, Phase 01-S review gate

**Purpose:** make the transition to OpenCode as development interface safe and reproducible. This file is a handoff, not permission to start a new phase automatically.

## GitHub source of truth

- Repository: https://github.com/daboolgame123-creator/Carlos-RPG
- **Working review branch:** `simulation-engine-phase-01s` (do not use `main` as the implementation branch).
- Parent audited behavior: `simulation-engine-phase-01r`, commit `0770498a1f257a252a82fde5ade1c43d3a791e3f`.
- Last code-tested commit before handoff docs: `7471938aae09197bcea1ab27dd9290b528ad5294`; **final HEAD should be fetched and checked afresh**.
- Schema **13** / Rules **17**. Prior 01-R SQLite worlds 12/16 are intentionally rejected. P0 long-lived-world save gate remains **OPEN**.
- Last reviewed behavioral CI: GitHub Actions run `41855607762`, **481/481 tests** on Python 3.10 and Python 3.13. Run CI again on the current head; do not rely on old run alone.

## Required reading before any edits

1. `simulation/docs/ROADMAP.md` — living plan and stage dependencies.
2. `simulation/docs/DEVELOPMENT_PROTOCOL.md` — staged review/closure protocol.
3. `simulation/docs/phase_01s_report.md` — implemented changes and limits.
4. `simulation/docs/phase_01s_review_request.md` — independent sign-off checklist.
5. `simulation/docs/phase_01s_internal_review.md` — two reproduced and fixed audit findings; **not independent approval**.
6. `simulation/docs/SAVE_COMPATIBILITY_POLICY.md` and `simulation/docs/ROADMAP_CHANGELOG.md`.
7. `simulation/docs/architecture.md`, `simulation/docs/decisions.md`; root `AGENTS.md` and original story files as **read-only context** when needed.

## First task in OpenCode — independent reviewer (not the builder)

The original implementing assistant found and corrected:
- Navigation incorrectly overridden food-seeking even when the NPC was standing at a visible source.
- A character ignored a personally received danger warning with confidence 95.

**Review them independently and review the remaining Phase 01-S diff, read-only first.** Verify trusted policy provenance, location privacy, ownership conservation, chronological resolutions, time/closed-session rejection, event replay/snapshots, old-world refusal and feature-off parity. Produce a standalone reviewer verdict `APPROVED` or `BLOCKED`, including exact source refs and tests. If blocker: report before changes; then with user approval/builder separation correct it, retest and review again. **No transition to 01-T while approval is pending.**

## Local commands (Python >=3.10)

```bash
git fetch origin
git switch simulation-engine-phase-01s
git pull --ff-only origin simulation-engine-phase-01s
cd simulation
python -m pip install pytest
python -m compileall -q src tests scenarios
python -m pytest -q
# Linux/macOS:
PYTHONPATH=src python scenarios/test_village/demo_foraging.py
```

On Windows PowerShell, run `$env:PYTHONPATH="src"` then `python scenarios/test_village/demo_foraging.py`.

**Do not** change Git branches or fetch destructively if local uncommitted work exists. Inspect `git status` first. If the remote branch is unavailable or behind local work, stop and reconcile explicitly.

## After distinct reviewer approves

- Document reviewer identity/method, independently identified risks and verdict in `phase_01s_report.md`.
- Change the 01-S ROADMAP status from pending to completed **only after** last-commit Python 3.10/3.13 CI passes and any blockers are resolved.
- Commit/tag/push according to the user's explicit workflow; never push `main` or rewrite history automatically.
- **Only then** present Phase 01-T design (NPC-local memory of resource sites, provenance of observations/hearsay, stale beliefs). Implementation begins when requested and tested per living roadmap.

## Permanent guardrails

- No implicit resource creation, no omniscient NPC knowledge, no unstated event semantics, no background wall-clock changes.
- Do not modify original Carlos story documents or world-state canon as if experimental fixtures were canonical.
- Do not migrate, delete or rewrite important saves without a vetted P0 backup/migration plan and explicit approval.
- Keep small-world behavior tests (~7 NPC) by default; use 100–150 only for justified performance checks.
- Separate code review role from implementation role where possible; passing tests do not replace independent inspection.
