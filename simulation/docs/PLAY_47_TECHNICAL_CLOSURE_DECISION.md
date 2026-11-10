# PLAY-47 — gated technical closure decision

Prepared 2026-11-10 UTC. Schema **42** / Rules **57**.

**Decision on verified promotion:** `CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER`.
**Before that promotion:** `OPEN / RELEASE NO-GO`.

This is a reviewable closure proposal on its candidate branch. Its existence,
the parent code's green checks, or one completed Python job does not enact the
decision. The decision takes effect only when **all** gates below pass on the
exact commit containing this document and that same commit is fast-forwarded
to `feature/play47-npc-economic-endurance-20261109`.

## Required activation evidence

1. **Exact source.** The candidate descends from the verified integration stack
   at `77ddb54b82038075c2d9ec642b8d0dcd3b75c43d`. Each workflow checks out and
   asserts the actual candidate SHA, rather than relying on a PR merge label.
   This proposal changes documentation only relative to runtime/test source
   `0f8c31f15e065cdc2d101bdfa6ca9b67d3331bdf`.
2. **Full checks.** Both Python 3.10 and 3.13 jobs in `simulation-tests.yml`
   conclude SUCCESS on this exact candidate, including the historical runtime
   and saved-world compatibility steps. The unchanged suite has 1,694 cases
   per Python at the runtime baseline; any failure or unexpected omission must
   be resolved before activation.
3. **Targeted checks.** All four audit/endurance jobs in
   `play47-economic-audit.yml` conclude SUCCESS on this exact candidate. Per
   Python, require the 176-case audit, the separate authentic 41/56 old-save
   refusal, and both seven-day wet/dry cases. No missing, cancelled, skipped or
   failed required job is counted as successful. Inspect the actual source SHA
   and the final reports in the logs.
4. **Economic and persistence results.** Require twelve initialized copper
   conserved, finite food/grain/water reconciliation, real courier roads and
   cargo custody, funded nonduplicated wages, local seller/road knowledge,
   daily SQLite close/reopen and full genesis replay through day seven,
   snapshot/PRAGMA checks and full semantic clock equivalence at hour 96.
   Compare both Python versions' wet/dry reports; investigate any divergence.
5. **Atomic promotion.** Re-read the candidate head and integration ref. Verify
   ancestry, then advance the integration branch without force or a `main`
   update. Re-read the remote ref after the update. Record the effective SHA,
   UTC date, final run links and decision in the closure PR and in
   [the parent review record](https://github.com/daboolgame123-creator/Carlos-RPG/pull/60).

While any gate is pending, PLAY-47 stays OPEN and PLAY-48 must not begin.

## Accepted experimental outcome

The approved [closure plan](PLAY_47_CLOSURE_PLAN.md) allows a documented finite
resource/distribution failure. The seven-day experiment uses one real joined
thirteen-resident food/water and ore/fuel/smith/repair world with full NPC needs.
The dry world starts with two water units; the wet world adds exactly six
units through three finite receipts at hours 24, 48 and 72. Neither receives
free bread, minted copper or player-directed NPC purchases.

The fully verified runtime baseline `0f8c31f` passed **1,694 full** and
**179 targeted** checks per Python (176 audit + 1 authentic old save + 2 endurance).
Its full run is [42719791538](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42719791538)
and targeted run is [42719785455](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42719785455).
Both runtimes' complete wet/dry checkpoint reports are identical and record
the following at hour 168:

| Measure | Dry | Wet |
| --- | --- | --- |
| Copper | 12 | 12 |
| Food / grain remaining | 6 / 3 | 5 / 10 |
| Water remaining, including cargo | 0 | 5 |
| Residents at maximum hunger | 13 / 13 | 13 / 13 |
| Deliveries: Huda / Hana | 3 / 24 | 3 / 25 |
| Additional deliveries after hour 72 | 0 | 0 |
| Additional bakes, growth, trades or wages after hour 72 | 0 | 0 |

These outcomes are acceptance expectations to reconfirm on both Pythons in
this final candidate, not a claim that its pending checks have already passed.
The [evidence report](PLAY_47_CLOSURE_EVIDENCE.md) retains the baseline source,
genuine run identities, custody failure reproducers and local observations.

The finite opening loaf provision delays Hana's hunger without adding
deliveries. At hunger 80 the existing courier leg can still run, but reserved
copper cannot finance even a one-coin meal. A future compensation mechanism
needs a real payer, completed-delivery entitlement, one settlement per unique
receipt and separate personal ownership or an explicit local food beneficiary.
No such wage/account rule is introduced by this closure.

## Limits preserved by the decision

- No seven-day self-sufficiency, recovery, renewable extraction, recurrent
  courier compensation or repeated nonfood production loop is claimed. A
  recovery claim would require a real post-stall delivery and an attributable
  later production or purchase; the measured worlds do not have one.
- The long joined fixture contains food plus ore/fuel/smith/repair. Wood and
  other professions retain their separate legacy regression coverage; this
  report does not present them as a seven-day joined wood-production trial.
  Repeatable physical chains remain the approved PLAY-48 scope after activation.
- Independent review remains `EXTERNAL_REVIEW_DEFERRED_BY_OWNER`; this is author
  self-review plus automated tests, not independent approval.
- `P0_PRODUCTION_NOT_APPROVED` remains. No public service, production save
  migration, durable-save support, `main` merge or original story change follows.

If the activation gates pass and the exact tested decision commit is promoted,
the first remaining PLAY-47 technical blocker is **none**. If they do not, name
the missing gate precisely and keep the phase OPEN.
