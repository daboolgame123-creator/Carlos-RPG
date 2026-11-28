# WORLD-01f Player Miner Contract Analysis — 2026-11-27

## Verified starting point

- Branch: `feature/carlos-world01c-finite-mine-20261127`, HEAD
  `9e91ac0b955dace15ee67ffeb969bbacbf75a08d`.
- The code/test SHA `05dfdb13e910cfca6161c1ae7cd186b50e274ec1` passed the complete
  Python 3.10 and 3.13 suites in Actions
  [#45977485506](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45977485506):
  1953 passed, 1 skipped for each version.
- PR #185 is still an open draft at its original head
  `416e26b6c037b2fc504c8454d9b607aadeee7eba`. No change to `main`, story files, or
  the PR is in scope.
- The proposed additional full-life depletion check is already covered by WORLD-01e:
  after the finite inputs are consumed, the world continues advancing, exactly one
  production job per NPC remains, and a second empty-mine attempt is rejected
  atomically. No separate depletion feature is justified by current evidence.
- `PlayerGateway.work` and `player_worker_id` are already generic. Baker and
  blacksmith player contracts have tests; WORLD-01c/d exercise the miner recipe only
  with an NPC. `production.configure_recipe` requires the named worker to be a real
  player, and `start_production` enforces that worker, physical site, tools, actual
  inputs, and funded wages through the existing reducer.

## Goal and classification

Prove that Carlos can explicitly choose and complete one timed, funded miner job
against the same kind of finite iron reserve used by WORLD-01c/d. This is a
test-only capability proof in a disposable event-sourced world, not a permanent
career assignment. There is no evidence for adding a new role system or reducer.

Classification: `CHAT_EXECUTABLE`.

## Planned world and scope

Add `simulation/tests/test_world01f_player_miner.py` with a minimal trusted bootstrap:

- One home, one iron mine, and a real 60-second route; Carlos is a player at home.
- At the mine: exactly one `iron_ore_reserve`, zero opening ore, one pickaxe, and two
  copper. Carlos starts with zero copper. Every quantity is declared at genesis.
- One 120-second `miner` recipe names Carlos in `player_worker_id`, consumes the
  finite reserve, produces one iron ore, and pays one copper from the mine.
- Carlos must travel and invoke `PlayerGateway.work`; neither travel nor waiting may
  start work automatically. The world has no NPCs or unstated supply behavior.

Do not change engine source, Schema46, Rules73, production rules, the main story, UI,
`main`, PR #185, or persistent saves. Keep this isolated from the original story.

## Acceptance criteria

1. At genesis and after arrival there is no production job, no output ore, and Carlos
   is not represented as an NPC. Starting the contract from home is rejected without
   changing the event-sourced state.
2. Only Carlos's explicit work command at world time 60 starts the job. It consumes
   the one reserve immediately, leaves the pickaxe intact, and does not expose ore or
   pay a wage at world time 179.
3. At the job's exact due time, world time 180, the one ore appears and one copper
   transfers from the mine's declared balance to Carlos. The two-copper total remains
   conserved.
4. A second attempt after depletion is rejected atomically while the mine still has
   one copper; no second job, ore, wage, or event is partially applied.
5. `verify`, event replay, snapshot, database integrity, and SQLite reopen reproduce
   the completed state. Rules/schema versions remain unchanged.
6. Run the new test with the existing player-work, finite-mine, and WORLD-01
   regressions, then the complete Python 3.10/3.13 suite and exact-head Actions.

## Risks and execution gate

- `production_jobs[*].npc_id` remains the historical worker identifier for the
  player job. Existing validators intentionally allow this when the recipe explicitly
  names `player_worker_id`; the test must assert Carlos remains a player and is absent
  from `state.npcs`.
- An explicit contract is not a durable profession selection. Do not claim otherwise
  or add career state as part of this test.
- If the generic reducer completes the contract with the declared balances, keep the
  change test-only. If it fails, inspect the exact event and failure before any engine
  patch; do not add opening stock, wages, migration, or a special miner rule.

## Verified outcome

The test passed on Python 3.12.14. The six-file player-work, mine, and WORLD-01
regression bundle passed **17 tests** on Python 3.10.22, 3.12.14, and 3.13.5. The
complete `simulation/tests` suite passed **1954 passed, 1 skipped** on Python 3.10.22
and 3.13.5. GitHub Actions
[#45987206045](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45987206045)
passed both jobs on exact code/test SHA
`ad0927a53d79f98b9b82ff709aed0fd5c15232a8`, with 1954 passed and 1 skipped per
version.

No engine, schema, rules, story, UI, or persistent-save code changed. The result proves
one explicitly chosen, time-bounded miner contract from a finite reserve; it does not
create a permanent profession state. Status: `WORLD-01f CLOSED_TECHNICALLY /
EXTERNAL_REVIEW_DEFERRED_BY_OWNER`. WORLD-01 remains open and production-save approval
remains `P0_PRODUCTION_NOT_APPROVED`.

The earlier candidate of another full-life depletion test is redundant: WORLD-01e
already verifies one job per NPC after source use, extended world time, and atomic
rejection of an empty-reserve attempt. Next, analyze whether Carlos's player-mined ore
can join the existing physical delivery and blacksmith contract path without new
resources or engine rules.
