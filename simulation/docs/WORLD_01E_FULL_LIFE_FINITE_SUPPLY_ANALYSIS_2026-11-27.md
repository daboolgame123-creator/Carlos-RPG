# WORLD-01e Full-Life Finite-Supply Analysis — 2026-11-27

## Verified starting point

- Active development branch: `feature/carlos-world01c-finite-mine-20261127`.
- Current documentation HEAD is `be9d03c4d3ee64a1ee7280c37910ab2ddb0362ad`;
  the code/test SHA `7b5dddb5d1d51c0432bf2870672edd1c68e783e4` passed Actions
  [#45922155158](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45922155158)
  on Python 3.10 and 3.13. PR #185 remains an open draft at its original head.
- `test_world01d_integrated_finite_supply.py` proves finite mine and timber inputs,
  physical charcoal procurement, and Carlos's funded forge contract, but its engine
  deliberately sets `economy_only_enabled=True`.
- `test_play47_joined_professions.py::test_full_life_flag_rejects_incompatible_modes`
  and `test_joined_full_life_npcs_really_trade_smelt_and_get_hungry` exercise
  `professional_full_life_enabled=True`, survival and consumption alongside multiple
  NPC professions. That world opens with one iron ore and one charcoal already at their
  sellers; it does not join finite iron extraction to that full-life market chain.
- The event-sourced bootstrap already represents world setup as ordered, validated
  `DomainEvent`s committed with the trusted `bootstrap=True` capability. A general
  `WorldBlueprint` would be an authoring convenience without a concrete consumer, so
  this task will not introduce one.

## Goal and classification

Prove that the finite supply chain from WORLD-01d still completes when the existing
full-life NPC policies, needs, and consumption are active. Keep the test-world setup
and actor commands unchanged. This is a test-only task unless a reproducible engine
defect blocks a legal, funded action.

Classification: `CHAT_EXECUTABLE`.

## Proposed implementation

- Extend the WORLD-01d integration test to exercise both focused-economy and full-life
  engine configurations using the same declared endowments, routes, workers, recipes,
  and player commands.
- In the full-life case, use the existing required flags:
  `economic_enabled`, `agriculture_enabled`, `navigation_enabled`, `routines_enabled`,
  `consumption_enabled`, `survival_enabled`, `supply_enabled`,
  `multi_professional_markets_enabled`, `compound_procurement_enabled`, and
  `professional_full_life_enabled=True`; set `economy_only_enabled=False`.
- Do not enable foraging, emergency assistance, relief, food-for-work, or wage-refill
  policies. The scenario opens without food; hunger may rise naturally. No survival
  outcome is an acceptance target.

## Invariants and risks

- Keep the existing one-unit mine and timber reserves, zero opening ore/wood/charcoal/
  fitting, explicit 8-copper total, and the same funded wages and tools.
- No new resources, routes, knowledge, jobs, money, migrations, story/UI changes, or
  main/PR #185 changes. Every purchase and delivery must retain the existing physical
  co-presence and custody assertions.
- Full-life needs may add events and shift timing. Check that hunger/consumption does
  not silently interrupt or rewrite the funded production contracts. If it blocks a
  legal action, inspect the event sequence; fix only a demonstrated common engine
  defect, never relax ownership or add rescue behavior to force success.
- Replay, snapshot, reopen, event order, balances, and material conservation remain
  authoritative. The broader economy and population survival remain unclaimed.

## Acceptance criteria

1. Both engine modes pass the same finite extraction → local sale → physical timber
   purchase/delivery → charcoal production → Carlos purchase/delivery → funded forge
   contract chain.
2. In full-life mode, all three NPC jobs and three market trades occur once from the
   declared source quantities; the mine retry after depletion remains an atomic
   rejection.
3. All 8 opening copper units remain conserved, all wages have an identified funded
   payer, and no food or other material is fabricated or consumed. Natural hunger may
   increase; no hunger ceiling or survival promise is required.
4. `verify`, snapshot, replay, and database reopen reproduce the final state in both
   modes; no unexpected or partially applied event remains after rejection.
5. Run this integration test and the existing WORLD-01b/c plus PLAY-46/PLAY-48M and
   PLAY-47 full-life regressions, followed by the full Python 3.10/3.13 suite and
   exact-head GitHub Actions.

## Affected files

- `simulation/tests/test_world01d_integrated_finite_supply.py` — add the full-life
  configuration and assertions while retaining the focused-mode regression.
- This analysis, `WORLD_01D_INTEGRATED_FINITE_SUPPLY_ANALYSIS_2026-11-27.md`,
  `WORLD_01_ANALYSIS_2026-11-27.md`, `WORK_QUEUE.md`, `ROADMAP.md`,
  `ROADMAP_CHANGELOG.md`, and `CARLOS_NEXT_CHAT_HANDOFF.md` — record only verified
  outcomes.
- No engine source/schema change is expected.

## Execution gate

First run the focused full-life case. If existing reducers and policy flags complete
the finite chain, keep the change test-only. If they do not, stop and classify the
specific failure before considering an engine patch. Keep WORLD-01 and
`P0_PRODUCTION_NOT_APPROVED` open until their own broader gates are satisfied.
