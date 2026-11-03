# Phase 01-I — Autonomous social initiative (prototype)

## Implemented

- An opt-in `LivingWorldEngine(..., social_enabled=True)` mode lets idle NPCs initiate short, **typed and deterministic** social exchanges during an **explicit** player-time advance. The manual clock and earlier action/navigation behavior remain unchanged when social mode is off.
- A pure `choose_social_intent` planner considers the **speaker's** hunger, safety, fatigue, directed trust, and recorded previous encounters. It selects among *greeting*, *request_help*, *offer_help*, and *threat*. It never reads another person's private needs, motives or beliefs.
- Only co-located, idle, non-traveling NPCs may be senders or recipients. Player character Carlos is never selected as an automatic partner. Pending manual intentions retain priority. Deterministic NPC IDs and recipient IDs break ties.
- Autonomous interactions emit `SocialMessageSent` and `SocialMessageReceived` inside the **same atomic advance command**, retaining the original social model's receiver-specific, asymmetric trust results and replay integrity. Result objects include `social_message_ids` for test/audit use.
- Social initiatives are bounded: at most one outgoing initiation per actor per **180 simulated seconds** and no repeat of the same speech-act type toward the same recipient within **900 simulated seconds**, based on recorded history. This is not a substitute for a full social effort/attention model.
- There is no simulation while the application/session is closed or no explicit logical-time command is running. All operations are offline and entirely local.

## Verification

Run from `simulation/`:

```bash
python -m pytest -q
python -m compileall -q src tests scenarios
PYTHONPATH=src python scenarios/test_village/demo_social_autonomy.py
```

**241 tests passed locally after review** (216 baseline + 22 Phase 01-I tests + 3 review regressions). Compilation passed and the isolated three-NPC social demonstration completed. In 360 simulated seconds after a manually recorded initial greeting, Aaron initiated a request to Bella at time 0, greeted Zora at time 180, and requested help from Zora at time 360. The world recorded six completed routine actions. No resource transfer or physical assistance was fabricated. The exact composition can change if the test rules change; the test fixture is not Carlos story canon.

Regressions cover first contact, asymmetric receiver trust, opting out, 180-second sender cooldown, 900-second repeated-topic cooldown, alternate partners, manual intention priority, busy/traveling/non-co-located guards, player exclusion, hunger-based help request, trust-based goodwill and hostility, event-budget rollback, invalid options, empty worlds, navigation co-existence, snapshot/restart, deterministic replay, equivalent split-step outcomes and non-disclosure of recipient-private needs.

## Non-goals and cautions

- A `request_help` is **not** actual aid and an `offer_help` is **not** a fulfilled promise. Neither spends time nor inventory and neither creates a debt or obligation.
- Generated dialogue remains **fixed templates**; no autonomous natural-language generation, lying, negotiation, rumor propagation, reputation, alliances, trading, economic consequences or combat is included. The existing reception model's trust delta is intentionally simplistic.
- Partner choice is a small rule-based policy, not a general purposeful social planner. New contacts occur automatically when the NPC is idle and other eligible characters are present; richer temperament/consent/attention rules remain future work.
- Cooldowns are enforced at the **autonomous planner** boundary and do not restrict authorized manual social interactions beyond previous Phase 01-H event guards.
- Internal capability flags are not security for untrusted HTTP callers. No GitHub CI was run; reported tests are local.
- **Schema 8 / rules 10 unchanged:** the phase adds no event type or database migration, only orchestration over existing social events. Existing prototype worlds with the same versions continue to replay. No Carlos game/story data was imported or changed and `main` remains untouched.

## Status

Implementation and post-implementation review completed for the Phase 01-I prototype scope. The next phase remains separate and requires authorization.

## Post-implementation review — 2026-11-04

**Confirmed finding: recipient-private intention leaked into social partner selection.** The original social planner used the same eligibility function for the speaker and all possible recipients. That function inspected `last_decision` at the current tick, although an unstarted decision belongs to the recipient's private state. A newly recorded private action intention could therefore make an otherwise visible, idle NPC disappear from the sender's potential conversation partners. This allowed the sender's choice to change based on information that character could not know.

**Fix:** Distinguish physically observable unavailability (an active action or travel) from a pending private intention. The initiating NPC may use **its own** pending decision to prioritize it over social speech, but the initiator may not read another person's pending decision. A physically busy recipient remains ineligible. No schema, reducer or event format was changed.

**Regression evidence:** Three new tests first failed on the previous implementation and now pass: a private recipient decision leaves partner selection unchanged; a physically busy recipient is still excluded; the integrated living-world coordinator can greet a recipient with a pending private decision without overriding that decision. The complete local suite passed **241/241**, Python compilation succeeded, and the test-village demo ran successfully. The corrected source and three regression tests were uploaded to GitHub and verified by exact Git blob SHA matches. Hosted GitHub CI has **not** run.

**Disposition:** Ready to close Phase 01-I within its limited prototype scope. The 180-second and 900-second automated cooldowns remain. No autonomous resource-backed assistance, unrestricted dialogue generation, off-session world advancement, or Carlos narrative changes were introduced. The current branch remains unmerged into `main`.
