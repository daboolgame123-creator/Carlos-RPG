# Carlos RPG — new-conversation handoff (living pointer, 2026-11-09)

**Read before continuing any development.** This file is a durable orientation document. Its status snapshot is historical; **always fetch current GitHub branch, PRs, CI and authoritative reports before acting**.

- Repository: `daboolgame123-creator/Carlos-RPG`.
- Canonical working branch at this checkpoint: `feature/play46-multi-input-atomic-recipes-20261109`.
- PLAY-46 implementation snapshot: Schema **42**, Rules **57**, code SHA `6020b92c443042ea81ef76b6b637ae10961b4d02` (before this planning-only document), PR #40 Draft. No `main` merge.
- Verified at snapshot: historical full CI #42609660548 successful, **1,694 passed on each of Python 3.10 and 3.13** at the same code SHA; targeted PLAY-46 CI #42613658371 successful. Newer #42613666694 was still in progress at the snapshot (3.13 green, 3.10 awaiting conclusion). Check its final state and any subsequent CI on the latest HEAD.
- **Current directive from owner:** prepare to use the next model allowance efficiently to progress toward a significantly more developed autonomous medieval NPC economy with visible play. Work in batches, plan before code, no invented economic subsidies, no bypassing stage gates.
- Detailed 46→51 staged plan: [CARLOS_ACCELERATION_PLAN_2026-11-09.md](CARLOS_ACCELERATION_PLAN_2026-11-09.md).
- Exact OpenCode model names and effort choices transcribed from screenshots: [OPENCODE_AVAILABLE_MODELS_2026-11-09.md](OPENCODE_AVAILABLE_MODELS_2026-11-09.md).
- Agent authority and stage safety: root [AGENTS.md](../../AGENTS.md), [DEVELOPMENT_PROTOCOL.md](DEVELOPMENT_PROTOCOL.md), [WORK_ROUTING_PROTOCOL.md](WORK_ROUTING_PROTOCOL.md), [WORK_QUEUE.md](WORK_QUEUE.md), and [WORLD_FIRST_ECONOMY_PRINCIPLES.md](WORLD_FIRST_ECONOMY_PRINCIPLES.md).
- **Start workflow:** (1) inspect actual branch and latest SHA/CI/Schema/Rules; (2) resolve PLAY-46 remaining technical gate first; (3) then open PLAY-47 with 7–10 NPC multi-day endurance and real 24h/72h/7d metrics; (4) proceed to 48 repeatable supply/production, 49 varied shops, 50 builder home, 51 inter-village trade only after respective gates; (5) use ChatGPT as primary, OpenCode on scoped need, with the model+effort routing file; (6) report succinctly with evidence, no implicit background work.

When delegating to OpenCode, identify **what ChatGPT handles, what OpenCode handles**, exact base SHA/branch, ownership of paths, expected tests, and stop rules. If OpenCode is inactive, do not pretend it is operating.
