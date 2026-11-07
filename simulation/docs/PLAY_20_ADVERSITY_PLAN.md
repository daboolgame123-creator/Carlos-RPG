# PLAY-20 — Village adversity and counterfactual survival: analysis and acceptance plan

Date: 2026-11-07. Status: CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER.
Base: simulation-engine-phase-play-19-integrated-village-journey @ 3a4b69e9ca8cd372063692e8d8dd4e8a185ab001.
Working branch: simulation-engine-phase-play-20-village-adversity.
Scope: disposable simulation world only; no original story files, main merge, schema or rules changes.

## Verified baseline

PLAY-19 uses ResumableTestSession, seven NPCs and living_player_gateway. Its tested journey ends at logical t=201. The engine caps each advance at 1,000 events, and reports that overflow without SQLite commit. NPC-owned food and hunger are supported only with setup_living_npc_survival_world and npc_survival_demo=True. Bread, coin, wild food and NPC-owned food are distinct resource ledgers. The existing living fixture starts with 3 seller-owned bread, 10 player-owned copper, 2 square + 4 woods wild food, and 2 NPC-owned food. Player hunger and medical effects are explicitly not modeled.

## Work package, risks and expected tests

| Task | Analysis and implementation plan | Acceptance |
| --- | --- | --- |
| PLAY-20a | Two physically plausible player paths: buy all/eat versus buy one/return gift; allow other NPCs to act autonomously | Divergent player outcomes, identical starting fixture, 7 NPC retained; player choices explicit only |
| PLAY-20b | Busy seller, remote seller and exhausted offer reject transactions; travel takes time | Rejected commands do not change event ledger, balances or revision |
| PLAY-20c | Four bounded 60s forage actions exhaust woods' finite food; empty eat/forage attempts rejected | Source and inventory decrement exactly; no mint/double spend, no teleport |
| PLAY-20d | Advance in smaller explicit waits to a finite horizon (initial default 3,600 seconds) with opt-in NPC hunger; save and resume | Check NPC stock consumption and conservation; SQLite verify equals load and snapshot; no time passes on reopen; duplicate/stale commands rejected |
| PLAY-20e | Compare two separate SQLite files for determinism; safe player handoff; dual Python CI | Player export excludes hidden NPC state, report has player/audit scopes, Python 3.10/3.13 full regression and targeted tests on final SHA |

## Constraints and failure modes

- Do not interpret a one-hour successful run as proof the village survives days. Record the tested duration precisely; any longer run must be separately verified.
- Avoid a single huge wait that exceeds the atomic event budget; this is not a mechanic change.
- No simulator-initiated decisions by Carlos, no fabricated earnings or food, no NPC private states in player-facing output.
- When present NPCs are unavailable, do not force interaction; rejected trades and empty resource actions are valid world outcomes.
- Verify command rejection is side-effect free, including no revision increment.
- Limit automated runtime; if a stress job becomes too slow or exceeds the event ceiling, adjust test time partitions transparently, not game physics.
- Keep PLAY-14g, 03-A7c, 03-A, production P0 and independent external review OPEN.

## Verification / closure gate

Start with focused PLAY-20 tests, then run whole repository suite on the final code commit for both Python versions and check GitHub Actions conclusions. Update evidence and only then set CLOSED_TECHNICALLY. Otherwise keep OPEN / VERIFICATION_PENDING with exact failed checks.
## Closure evidence (2026-11-07)

Verified code/test SHA: `cf9654b9017117397d4f03751e174a7a31bd8d76`. Full CI run [42400314460](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42400314460) = 1,470 passed per Python 3.10/3.13. Targeted run [42400314534](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42400314534) = 67 passed per version, including two real one-hour runs. See [PLAY-20 actual report](PLAY_20_ADVERSITY_REPORT.md). Production P0 and external review remain unapproved/deferred.
