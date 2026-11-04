# Phase 01-N — Independent review and closure

## Scope checked
Reviewed the production change from Phase 01-M to Phase 01-N. The runtime
change is confined to `simulation/src/carlos_sim/domain.py`: a fast native-JSON
thaw path, a detached-copy `WorldState.to_dict` on previously normalized
projections, and a `WorldState.from_dict` constructor that validates and
normalizes before freezing. No rule, event type, DB schema, or Carlos story
file was changed.

Independent source inspection checked that external snapshot validation,
strict direct-constructor serialization, frozen nested collections, event
application, session/capability checks and transactional commit remain on the
same paths. Tests also cover rejected inputs, invalid events, rollback, full
replay, detached copies and snapshot integrity.

## Independently executed GitHub Actions evidence
- First CI run: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41824279084
  - Python 3.10: **410 passed**
  - Python 3.13: **410 passed**
  - `python -m compileall -q src tests scenarios`: passed
- Cross-version CI run: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41824609633
  - Full regression suite and compile step: successful on both versions
  - Same `bench_event_parity.py` fixture used against the reviewed 01-M
    source and 01-N source; complete event-ledger and final-state digest
    output matched at **10 and 25 NPCs**, on both Python versions.
- Both workflows are available as a reproducible CI configuration in
  `.github/workflows/simulation-tests.yml`.

## Caveats and remaining work
- Local benchmark data in `phase_01n_validation.md` are single-sample timings
  recorded during implementation, not measurements from CI.
- The parity checks cover the defined scenarios, not every possible event.
- The high-level planner and SQLite commit path still each project a batch;
  whole-state validation per event remains a scaling concern.
- The CI check-out uses the named reviewed 01-M branch as baseline. If that
  branch changes, pin its reviewed SHA for durable future equivalence.
- No real Carlos story save was imported, modified or tested.

## Verdict
**Phase 01-N closed within the test-world simulation scope.**
The optimization is compatible with Schema 11 / Rules 15, with no migrations.
Performance results do not justify assuming production support for 1,000+
active NPCs. Further performance work must be independently phased and tested.
