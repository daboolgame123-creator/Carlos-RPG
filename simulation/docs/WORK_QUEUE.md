# Carlos RPG — سجل توجيه الأعمال القابلة للاستئناف

## أمر الاستئناف الفوري لأي محادثة جديدة — قرار 2026-11-07

**سياسة العمل:** دفعات تطوير، لا مهمة واحدة لكل «تابع». المرجع الأول `AGENTS.md` ثم `WORK_ROUTING_PROTOCOL.md` (التحديث المؤرخ 2026-11-07). المطلوب استغلال الفترة المحدودة للاشتراك للوصول إلى نسخة عالم **قابلة للعب**؛ 3–8 مهام مستقلة قابلة للتحقق في الدفعة إن أمكن، مع **التحليل أولًا**، اختبارات شخصيات/تزوير/SQLite، ثم CI نهائي على SHA محدد لكل Python 3.10/3.13. لا تتوقف بعد كل تعديل صغير ولا تضغط التقدم على حساب الجودة أو تخلق نجاحًا غير مثبت. لا تغيّر `main`.

**نقطة انطلاق موثقة قبل هذا التحديث:** الفرع `simulation-engine-phase-03a7c-observation-contract`، آخر نجاح شامل لشفرة المحرك `ba5e885a78056da842f0a8cbe2ada152e3729e8d` (GitHub Actions `42314040340` على Python 3.10 و3.13). آخر تعديل توثيقي قبل سياسة الدفعات `5e9ac61c`. **تحقّق من HEAD وCI مجددًا** عند البدء؛ لا تفترض أنهما لم يتغيرا.

**المهمة المفتوحة:** `03-A7c` (والأم `03-A`) ما زالتا `OPEN`. الذاكرة التاريخية لمشاهدة الراحة والرعاية مثبتة باختبارات؛ أما **مصدر علامة جسدية واقعية موثوقة** (عرج/جرح ظاهر...) فلم يُنفّذ، وممنوع اشتقاقه من رقم شدة الإصابة أو مجرد الراحة. ابدأ بتحليل اعتماديات المهمة وما يمكن إنجازه منها؛ إن كانت محجوبة، انتقل إلى أعمال مستقلة حقيقية على قاعدة خضراء، مع إعطاء أولوية للمسار الحرج نحو لعب كارلوس وليس التوثيق لذاته.

**ملاحظة تاريخية:** جدول ترتيب مهام J1c2b-CI أسفل هذه الفقرة هو سجل من فرع عمل سابق، وليس أمرًا لإعادة تنفيذ مهمة مغلقة أو لإيقاف العمل على 03-A7c. اعتبر أحدث تسجيل مؤرخ وحالة GitHub الفعلية مرجعًا، وصنّف كل دفعة قبل تنفيذها.


**آخر مراجعة:** 2026-11-06. **المرجع الحاكم:** [WORK_ROUTING_PROTOCOL.md](WORK_ROUTING_PROTOCOL.md). هذا سجل أولي حقيقي لما نعرفه حاليًا، وليس ادعاء بأن جميع المراحل المستقبلية قد فُصّلت أو اختُبرت. راجع HEAD وCI عند كل بدء.

| ID | عنوان | اعتماديات | تصنيف التنفيذ | الحالة | البيئة/الدليل | سبب التعليق أو خطوة التنفيذ |
|---|---|---|---|---|---|---|
| J1c2b-CI | إصلاح انحدار النسخة Schema29/Rules37 وبصمة التوافق الدلالي | آخر كود J1c2b على فرع 04a-j1 | `CHAT_EXECUTABLE` | `CLOSED_TECHNICALLY` | CI الكامل `42246881990` وadversarial `42246881991` ناجحان على `88c110e1c77d724424eb105a3fea0dd6d541bd3e`؛ محليًا 977/977 على 3.10 و3.13. | أُغلق السبب الجذري (إسقاط `local_institutions`) والافتراض المتقادم Rules 36. لا يُغيّر هذا اعتماد P0 أو المراجعة الخارجية. |
| J1c2b-REG | توثيق واختبار تسجيل مؤسسة تأسيسية محدودة الصلاحية | J1c2b-CI | `READY_FOR_VERIFICATION` | `CLOSED_TECHNICALLY` | نفس CI الناجح؛ أُعيد تمرين استعادة 7 أشخاص/38 حدثًا محليًا على `88c110e`، ورُفض ملف 28/36 حقيقي دون تغيير (sha256 `fffff56c…`). | إغلاق هندسي فقط؛ الاستعادة الإنتاجية/Windows الحقيقية تبقى `EXT-002`/`EXT-003` غير محققة. |
| J1c2b-LAW | قواعد شرعية السلطة ونقل ملكية قانونية نافذة | J1c2b-CI، تعريف منبع الحق وهوية الممتلكات والموافقة والجهة | `DECISION_REQUIRED` | `WAITING_DECISION` | لا يوجد قانون نافذ في Schema29/Rules37؛ المسودات غير ملزمة | وثّق التصميم والبدائل؛ لا تُنشئ ملكية ملزمة أو محكمة دون اعتماد العقد القانوني وقواعد الثقة. |
| EXT-001 | مراجعة خصومية مستقلة | حسب شروط التسليم | `EXTERNAL_EXECUTION_REQUIRED` | `WAITING_EXTERNAL` | [سجل الخارج](EXTERNAL_VALIDATION_LEDGER.md) | مؤجلة بقرار المالك، ليست نجاحًا؛ لا تمنع تطوير ميزات تجريبية مستقلة خالية من العيوب المانعة. |
| EXT-002 | تجربة استعادة فعلية على جهاز/سيرفر الإنتاج | البيئة النهائية ونسخ احتياطية معزولة | `EXTERNAL_EXECUTION_REQUIRED` | `WAITING_EXTERNAL` | [سجل الخارج](EXTERNAL_VALIDATION_LEDGER.md) | يمنع الاستخدام الإنتاجي إلى حين تحقق حقيقي؛ يمكن اختبار منطق مستقل على CI. |
| EXT-003 | اختبار النسخ والاستعادة على Windows المستهدف | بيئة Windows | `EXTERNAL_EXECUTION_REQUIRED` | `WAITING_EXTERNAL` | [سجل الخارج](EXTERNAL_VALIDATION_LEDGER.md) | غير مختبر؛ لا تفترض تكافؤ التشغيل مع Linux. |
| EXT-004 | توثيق هوية واجهة شبكة غير موثوقة | تصميم API وهويات/صلاحيات فعلية | `CHAT_PARTIAL_EXTERNAL_GATE` | `BLOCKED` | [سجل الخارج](EXTERNAL_VALIDATION_LEDGER.md) | يمكن وضع تصميم/اختبارات محاكاة هنا؛ يحظر كشف API للاعبين حتى تحقق الثقة والاعتماد الإنتاجي. |

## ترتيب الاختيار الفعلي عند «تابع»

1. عالج **J1c2b-CI** أولًا؛ لأنه عيب مانع في الفرع الحالي ويمكن التحقيق فيه بأدوات GitHub. لا تخفِه تحت بند «عمل خارجي».
2. بعدها أثبت **J1c2b-REG** على SHA ناجح وحدّث البوابات.
3. بالنسبة إلى **J1c2b-LAW**: افصل مهام التحليل التي يمكن إنجازها هنا عن قرارات صاحب المشروع غير المحسومة؛ لا تقفز من المسودة إلى سلطة قضائية.
4. تجارب `EXT-001` إلى `EXT-004` لا تعدّ منجزة. إذا وصلت إلى عمل يعتمد على أي منها، صنّفه `BLOCKED_BY_DEPENDENCY` وابحث عن عمل مستقل وفق بروتوكول التوجيه، ولا تجعل رقم المرحلة وحده مبررًا للتقدم.
5. أي مهمة جديدة تُضاف هنا **قبل البدء بها** برقم واضح، اختبار محدد، اعتماديات وتصنيف. لا تُعاد تسمية مهمة فاشلة إلى مهمة ناجحة.

**ملاحظة مهمة:** هذا الجدول لا يعني أن العمل على المراحل 03/04/05 متاح تلقائيًا؛ يجب إثبات أن المهمة المختارة مستقلة ويمكن تنفيذها على أساس أخضر. الوثيقة الرسمية [ROADMAP.md](ROADMAP.md) تصف المراحل الكبرى.

## OpenCode handoff (2026-11-06)

For the ready external desktop review, use [OPENCODE_VERIFICATION_HANDOFF_2026-11-06.md](OPENCODE_VERIFICATION_HANDOFF_2026-11-06.md). First fix J1c2b-CI semantic parity gate; then perform independent code review and isolated Windows backup/reopen drills. Do not mark the production server recovery or unimplemented network authentication as tested. Keep all logs tied to the final code SHA.

## J1c2b-CI evidence update (2026-11-06)

- **Observed failure:** full CI `42229493643` on code `617b931da5cc3b433525ae6410f5e878dfc87012` reported `976 passed` in pytest, then the Phase 01-T flag-off parity step failed with `legacy_semantic_digest` old `7d2be0d6c63594aaf7d6aa60f03be97a9c01747a7606931c66b2cc91c710bdf9` vs new `e665f86fb0e164dfa64095130ed75c8995c86f1d0922d8127d83a71264633157`.
- **Root cause (proven, not assumed):** J1c2b added the empty `local_institutions` collection to `WorldState` for Schema 29. `bench_event_parity.py` strips version fields and post-baseline empty collections, but its strip list had not been extended. Field-by-field comparison of the same seven-NPC/51-event run under genuine 01-S and current code showed: identical `events_digest`, identical values for every shared semantic field, and only the additional empty `local_institutions` key. No behavioral or event-log divergence was found.
- **Fix:** add `local_institutions` to the semantic projection in `bench_event_parity.py`, `bench_food_knowledge_parity.py`, and `bench_scarcity_disabled_parity.py`; add a regression guard in `tests/test_knowledge_compatibility.py` covering all three benches. No expected hash was replaced and no parity assertion was weakened.
- **Local verification:** Python 3.13 and 3.10 full suite each `976 passed, 1 skipped`. Parity restored exactly: 01-T `7d2be0d6…`, 01-U `e2fa8107…`, 01-V `ef830145…`; 02-F, 02-G and 01-R parity checks also pass locally.
- **First pushed CI (`42244658986`):** pytest and the adversarial workflow passed, but the 01-U parity step failed because the workflow still pinned the candidate to **Rules 36** while J1c2b had bumped it to **37**. This was a second stale version expectation, not a digest divergence.
- **Follow-up fix:** update the 01-U and 01-V candidate pins to 37 (baselines remain 18) and add `test_ci_parity_gates_pin_current_rules_version` so the next version bump cannot silently leave the workflow stale. Emulating both gate scripts locally now passes.
- **Exact-SHA CI (green):** [Simulation regression suite `42246881990`](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42246881990) and [adversarial `42246881991`](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42246881991) succeeded on `88c110e1c77d724424eb105a3fea0dd6d541bd3e`; both matrix jobs (Python 3.10/3.13) completed successfully. Local final-code suite: `977 passed, 1 skipped` on each.
- **Genuine 28/36 rejection:** created an actual Schema 28 / Rules 36 SQLite world with the predecessor code (`ecd79f0`), then opened it with the current code. `load()` raised `UnsupportedVersion`; world/event/snapshot rows and the whole-file SHA-256 (`fffff56c9d7dc5375acd6fd5b73662aeafa7dd7705d2a208ae8dead75532a893`) were unchanged, and `PRAGMA integrity_check` returned `ok`.
- **Status:** J1c2b-CI and the CI/tooling blocker on J1c2b-REG are `CLOSED_TECHNICALLY`. J1c2b-LAW remains `WAITING_DECISION`; production P0 and real Windows/server recovery remain external and unverified.


## Independent health branch work queue — 2026-11-06

| ID | Title | Dependencies | Classification | Status | Evidence | Next step |
|---|---|---|---|---|---|---|
| 03-A7a | Self-only, read-only injury decision advisory | Verified 03-A6 `2ca67e83` (Schema32/Rules40) | `CHAT_EXECUTABLE` | `IN_PROGRESS` | New independent `simulation-engine-phase-03a-injury-behavior` branch | Implement pure policy from own persisted injuries, reject cross-NPC leakage, run dual-Python full CI |
| 03-A7b | Integrate own-injury effect into deterministic NPC decision/event replay | 03-A7a exact-SHA green and planned replay contract | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | Requires verified 03-A7a read-only policy | Review NPCService/LivingWorldEngine/forage parity and version bump before editing |
| 03-A7c | Observations and disclosure of another NPC's visible injury | knowledge observation provenance + approved visibility contract | `DECISION_REQUIRED` | `WAITING_DECISION` | No general diagnosis or omniscient observer | Define observable symptoms and what NPC can infer |

## 03-A8a — health recovery reservation integrity (2026-11-06)

| ID | Task | Dependencies | Classification | Status | Evidence | Next |
|---|---|---|---|---|---|---|
| 03-A8a | Reject paid recovery without matching durable schedule at atomic append/replay boundaries | Verified 03-A6 and 03-A7b | `CHAT_EXECUTABLE` | `CLOSED_TECHNICALLY` | SHA `75dc8141`; CI `42290286511` — 1125/1125 on Python 3.10/3.13 | Recovery reservation invariant verified; external review deferred |
| 03-A7c | Cross-NPC visible symptoms and disclosure contract | Explicit observation/knowledge policy | `DECISION_REQUIRED` | `WAITING_DECISION` | Current engine does not establish diagnosis or peer knowledge | Do not implement auto-disclosure until visible symptom rules are adopted |


## 03-A7c observation decision draft — 2026-11-06

- **Task:** `03-A7c` — Cross-NPC visible injury observations.
- **Classification / status:** `DECISION_REQUIRED / WAITING_DECISION`; parent `03-A` still open.
- **Proposal:** [PHASE_03A7C_OBSERVATION_DECISION_DRAFT.md](PHASE_03A7C_OBSERVATION_DECISION_DRAFT.md) distinguishes optional, explicit local qualitative symptom observations from private injury truth and diagnosis. Owner has **not** approved the proposed defaults.
- **Next:** obtain owner choice between limited symptom observation and deferral; only then plan implementation, versioning, character adversarial tests, full dual-Python CI and exact-SHA verification. No injury disclosure code implemented by this documentation task.

## 03-A7c continuation — limited visible symptoms (2026-11-07)

Owner's "تابع" following the limited observation recommendation authorizes
the **qualitative local observation principle**, not a fabricated symptom
producer. See [implementation gate](PHASE_03A7C_IMPLEMENTATION_GATE.md).

| ID | Title | Dependencies | Execution classification | Status | Evidence / next step |
|---|---|---|---|---|---|
| 03-A7c-guard | Non-disclosure / SQLite reopen regression baseline | 03-A8a green | `CHAT_EXECUTABLE` | `VERIFICATION_PENDING` | Branch `simulation-engine-phase-03a7c-observation-contract`, tests at `f4121af6`; check final SHA dual-Python CI |
| 03-A7c-source | Trustworthy visible symptom provenance | Supported physical action/outcome source | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | Do not derive limp/collapse from injury severity alone |
| 03-A7c-observe | Explicit observer-scoped local knowledge event | 03-A7c-source | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | Deterministic visibility and trusted provenance required |
| 03-A7c-replay | Full adversarial/snapshot/replay/parity acceptance | 03-A7c-observe | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | NPC scenarios + Python 3.10/3.13 exact-SHA CI |

The earlier `DECISION_REQUIRED` entry is a dated historical gate, not a claim
that 03-A7c was implemented or closed. Parent 03-A stays OPEN.


## 03-A7c factual activity evidence — 2026-11-07

| ID | Title | Dependencies | Classification | Status | Evidence / next |
|---|---|---|---|---|---|
| 03-A7c-rest-evidence | Project only the visibly running rest action under a recorded local sighting, without injury inference or automatic memory | 03-A7c-guard, existing action schedule / NPCObserved | `CHAT_EXECUTABLE` | `VERIFICATION_PENDING` | Code `62cdd7b0`, multi-NPC/healthy-vs-injured/reopen tests `67af6c2a`; verify full Python 3.10/3.13 CI on latest SHA |
| 03-A7c-medical-sign-source | Record validated *physical injury symptom* from causal injury/action evidence | Real physical sign source, not numeric severity or resting alone | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | Visible rest is not a medical observation; no fabricated limp or collapse |
| 03-A7c-observer-memory | Persist historical qualitative health observation scoped to observer | 03-A7c-medical-sign-source and trusted event contract | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | No auto-sharing, diagnosis, severity leak, or player-view expansion |

This is a bounded independent 03-A7c slice, not parent completion.


## 03-A7c local scene projection — 2026-11-07

| ID | Title | Dependencies | Classification | Status | Evidence / next |
|---|---|---|---|---|---|
| 03-A7c-scene | Return only observer-scoped, current-tick visible resting activity for a recorded local NPC sighting | Existing verified 03-A7c rest evidence and NPCObserved | `CHAT_EXECUTABLE` | `VERIFICATION_PENDING` | Pure projector at `461d0285`, seven-NPC tests at `2a010ac0`, final SHA CI required; no medical inference, event, or claim persisted |
| 03-A7c-medical-source | Evidence-backed physical sign distinct from rest | Authorized physical source not reducible to severity | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | Cannot assert limp or collapse from injury ledger alone |
| 03-A7c-private-memory | Observer-scoped historical qualitative health claim | 03-A7c-medical-source and event/capability contract | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | Must reject fabricated symptoms and preserve replay across SQLite reopen |

The scene projection is not closure of the parent 03-A7c task.


## 03-A7c conservative interpretation — 2026-11-07

| ID | Title | Dependencies | Classification | Status | Evidence / next |
|---|---|---|---|---|---|
| 03-A7c-neutral-interpretation | Project a factually supported rest observation with explicitly unknown cause, identical for injured and healthy subjects | Verified 03-A7c local scene projector | `CHAT_EXECUTABLE` | `VERIFICATION_PENDING` | Code `e12a8221`, regression tests `4024d628`; require exact-final-SHA dual Python CI |
| 03-A7c-subjective-interpretation | Explain individually different suspicion using only observer-owned proven memories | Trusted observer historical knowledge evidence and approved inference policy | `BLOCKED_BY_DEPENDENCY` | `BLOCKED` | No subjective guess may be persisted as a medical fact |

This subtask does NOT implement durable symptom memory, an illness diagnosis or
the complete 03-A7c feature. Parent 03-A remains OPEN.


## 03-A7c observer-specific historical activity memory — 2026-11-07

| Task | Status | Evidence / qualification |
|---|---|---|
| 03-A7c-activity-memory | `VERIFICATION_PENDING` | Code `11fb80e6`, reducer `30f38247`, explicit atomic movement API `6329f6a8`; tests `151ced1f` and seven-NPC `cf9f1c91`; require exact final-SHA dual Python CI. Observer-only, visible-rest *behavior*, cause unknown; does not imply clinical health |
| 03-A7c-physical-signs | `BLOCKED` | No trusted physical limb/visible injury impairment source; rest alone is insufficient |
| 03-A7c-health-memory | `BLOCKED` | Requires clinical-sign source, separate medical observation policy, adversarial provenance validation |

No automatic observer knowledge, hearsay, treatment or merging. Parent 03-A OPEN.


## 03-A7c evidence check and pending idempotency follow-up — 2026-11-07

- `03-A7c-activity-memory-base`: `CLOSED_TECHNICALLY`, **not**
  `APPROVED` — GitHub Actions run `42305932829` on `91e6004e`;
  Python 3.10 and Python 3.13 both SUCCESS. Covers opt-in local
  visible-rest memory, healthy/injured indistinguishability, seven NPCs,
  SQLite replay and tamper rejection. External adversarial review deferred.
- `03-A7c-activity-memory-integrity`: `VERIFICATION_PENDING` — newer
  tests for duplicate same-tick observations, two separate remembered times,
  no invented acknowledgement, no automatic food-knowledge re-sharing,
  pending delivery deduplication and its later acknowledgement; latest
  test commit `90804577`, documentation follow-up on same branch.
- `03-A7c-medical-symptom-source`: `BLOCKED_BY_DEPENDENCY` — no
  trusted event-sourced physical symptom; no limp inferred from rest or
  severity.
- `03-A7c-medical-observer-memory`: `BLOCKED_BY_DEPENDENCY` on
  medical-symptom-source, distinct from proven behavioral resting memory.

No cross-branch merge and no closure of parent 03-A7c / 03-A.

## 03-A7c finite resting-memory capacity — 2026-11-07

- `03-A7c-memory-capacity`: `CHAT_EXECUTABLE / VERIFICATION_PENDING`.
  Source `61d8510a`, 65-distinct-tick integration test `1b7bf9af`.
  When one observer has 64 visible-rest memories, the next explicit
  `NPCObserved` must still commit; only additional memory projections are
  skipped. Pending inbox deliveries count against available capacity.
  Exact final-SHA Python 3.10/3.13 CI is required before closure.
- Previous idempotency regression `ccb09cc0` obtained GitHub Actions success
  at its own exact SHA; later pending-delivery and capacity changes must be
  tested independently.
- No medical-sign producer or health diagnosis created. Parent 03-A7c OPEN.


## 03-A7c memory integrity acceptance — 2026-11-07

- `03-A7c-memory-capacity`: `CLOSED_TECHNICALLY` after GitHub Actions
  `42307726165` on source-and-test SHA `8c3fc68165bb5f28548dfc07b150cbd14da5c519`:
  Python 3.10 SUCCESS; Python 3.13 SUCCESS. This verifies 64 pending
  deliveries do not admit a 65th forged direct delivery; the prior 65-tick
  accepted-memory and nonblocking-observation test is green on
  `9be0a4d0` run `42307467599` in both environments.
- `03-A7c-activity-memory-integrity`: `CLOSED_TECHNICALLY` for the
  tested behavior-only scope (not medical symptom detection).
- `03-A7c-medical-symptom-source`: `BLOCKED_BY_DEPENDENCY`.
  A numeric injury, fatigue, or rest is not ground truth for an externally
  visible limp, wound, or collapse. Never fabricate a medical sign.
- Parent `03-A7c` and `03-A` remain OPEN. No main merge.


## 03-A7c visible supportive-care follow-up — 2026-11-07

- `03-A7c-care-sighting` — `VERIFICATION_PENDING`: current read-only
  grounded projection `d97f39cd`; tests for actual funded Adel→Nora care
  `6f8f0813` (at that exact SHA, GitHub CI success), followed by new
  regressions `4ddc2eb1` for Adel departing while appointment remains
  pending, and snapshot/SQLite reopen without leaking care to Salma.
  Recheck final SHA dual Python CI before closing this narrow subtask.
- `03-A7c-physical-injury-sign` — `BLOCKED_BY_DEPENDENCY`: pending
  supportive care is *not* proof of a physical symptom or diagnosis.
  There is no trusted producer for limp/wound/collapse.
- `03-A7c` parent and `03-A` are OPEN; `main` unchanged.


## 03-A7c ordered care witnessing (2026-11-07)

- `03-A7c-ordered-care-evidence`: `VERIFICATION_PENDING`.
  The older same-tick care scene returned false evidence when a witness
  looked before the care activity started. Replaced with an opt-in
  `care_enabled=True` single-command `NPCObserved` +
  `NPCInformationDelivered` + `NPCBeliefReceived` sequence.
  Reducer validates physical care against treatment state; store requires
  the care delivery to follow the observer's own observation in that
  SAME append, and rejects a `RecoveryStarted` between them.
  Code commits `467b1fef`, `41016531`, `794dd725`, `26abe8f1`,
  `e33b1966`; regression tests `ac4717ac`, `376a04c9`,
  `ff43efbd`. Final-SHA dual Python CI required.
- Visible care still means only an external care interaction, never a
  guaranteed physical symptom or medical diagnosis. Parent
  `03-A7c` and `03-A` remain OPEN.


## 03-A7c historical supportive care recall — 2026-11-07

- Ordered care observation: `CLOSED_TECHNICALLY` against CI
  `42310095549` at `ebb0f8ee`, Python 3.10/3.13 both success.
- Historical care memory: `VERIFICATION_PENDING`; pure
  `recall_supportive_care` reads only the observer's previous validated
  `visible-care` belief, never injury severity, cause or resource details.
  Implementation `c1301fc9` and tests `b54b76b6` cover Basim retaining
  factual memory after Adel finishes, Salma/Huda/Omar not learning it,
  repeated observation not duplicating the record, time-zero look before
  care not predicting it, and snapshot/SQLite replay. Require final SHA CI.
- No actual physical wound, limp, collapse or medical diagnosis producer yet.
  Parent 03-A7c / 03-A remain OPEN; no merge to main.


## 03-A7c care-memory adversarial completion (2026-11-07)

- `03-A7c-care-memory-integrity`: `VERIFICATION_PENDING` — commit
  `3dfbc713` adds 65 distinct-tick care observations against a 64-memory
  ceiling while care remains genuinely pending and tests that forged
  recipient, caregiver or diagnosed illness cannot create accepted care
  evidence. Exact final SHA must pass the Python 3.10/3.13 CI.
- Prior tests for Basim/Salma observer-owned care memories after treatment,
  snapshot/replay and same-tick ordering remain mandatory. Parent
  03-A7c / 03-A still OPEN; physical injury symptom source not implemented.


## 03-A7c interruption witness test (2026-11-07)

- `03-A7c-historical-care-interruption`: `VERIFICATION_PENDING`
  at `9611616a`. Integration scenario: Basim observes Adel actually caring
  for Nora; Adel leaves via a timed physical route; care becomes invisible
  immediately, but the true older first-hand memory remains after the due
  appointment is interrupted. No refund, cure, omniscient knowledge for
  Huda, or revision/replay mismatch.
- Prior care-memory integrity and 65-tick history completed successfully
  on exact SHA `a109911e` (run `42311461630`, Python 3.10/3.13).
  Keep the new interruption test separate until its own final-SHA green run.
- The physical injury symptom model is still unimplemented; 03-A7c and
  parent 03-A remain OPEN and no change to `main`.


## 03-A7c — verified care memory and travel boundary (2026-11-07)

- `03-A7c-historical-care-interruption`: `CLOSED_TECHNICALLY` —
  GitHub Actions `42312139434`, commit `49d93f41`,
  both Python 3.10 and 3.13 SUCCESS. Adel's real departure leaves
  Basim's already witnessed care memory intact, while the unfinished
  funded appointment interrupts without miraculous healing.
- `03-A7c-historical-care-travel`: `CLOSED_TECHNICALLY` —
  GitHub Actions `42312298248`, exact commit `ab7c04a3`,
  both Python 3.10 and 3.13 SUCCESS. Basim keeps his prior
  factual memory after traveling away but gains no remote sight of care.
- `03-A7c-activity-and-care-behavioral-memory`: `CLOSED_TECHNICALLY`
  for the current limited *visible activity* scopes; full medical symptom
  observation is **NOT** complete. Previous dual-Python green tests cover
  observer identity isolation, 64-record limits, 65-tick witness trials,
  fake actor/source/time rejection, SQLite snapshots and replay,
  same-logical-tick event ordering, and genuine independent witnesses.
- `03-A7c-physical-symptom-source`: `BLOCKED_BY_DEPENDENCY` —
  source-of-truth still tracks injuries but no grounded visible wound,
  limp or other physical sign is produced by a verified event. Ordinary
  rest and supportive care are not such signs.
- `03-A7c` parent and `03-A` remain `OPEN`, no merge to `main`.
  Do not claim symptom observation or full gate closure on the basis of
  behavioral memory coverage.


## 03-A7c rest-sighting same-tick integrity (2026-11-07)

- `03-A7c-rest-scene-ordering`: `VERIFICATION_PENDING`.
  A plain `NPCObserved` only recorded occupants and a tick; it could
  falsely imply that the witness saw a rest action which started later
  in the same tick. The pure `observed_resting_activity` projector now
  also requires that observer's verified `visible-rest` first-hand
  belief minted by explicit `observe(activity_enabled=True)` while
  rest was actually running (`99a3f141`). The event-store append gate
  requires first-hand rest evidence to follow the same observer's
  `NPCObserved` inside one atomic command (`c36e5ebb`).
  Old read-only scene tests were updated to opt in to actual witness
  evidence; regressions include same-tick rest starting after a look,
  pending-delivery first-hand provenance, and time-bound replay
  (`709df6d9`). The changed observable-scene contract is opt-in and
  must pass Python 3.10 and 3.13 on exact final SHA.
- Strictly do not equate recorded rest with a physical injury symptom.
  The trusted visible limp/wound/collapse source remains
  `BLOCKED_BY_DEPENDENCY`; parent `03-A7c` and `03-A` remain OPEN.


## 03-A7c same-tick rest integrity — verified closure 2026-11-07

- `03-A7c-rest-scene-ordering`: `CLOSED_TECHNICALLY` at exact
  commit `ba5e885a78056da842f0a8cbe2ada152e3729e8d`.
  GitHub Actions run `42314040340`: both Python 3.10 and 3.13
  `SUCCESS`. Full suite covers direct and independent observation,
  pending delivery, no retroactive same-second rest memory, no causal
  diagnosis, replay, reopening, and backward-compatibility CI gates.
- Older intermediary commits had regression failures from tests still using
  passive observations, an invalid command ID, and an unsupported
  argument to the action service. All corrected in the verified head.
- `03-A7c` is **NOT CLOSED** as a parent: physical externally
  observable injury symptoms are still absent. A trusted physical
  action-result producer, rigorous event provenance and local
  qualitative witness pipeline remain prerequisites.
- Neither `main` nor schema/rules versions are changed.

## First playable-first batch — BATCH-PLAY-01 (2026-11-07, planned before code)

Independent of blocked `03-A7c` physical symptom producer; only the existing
trusted local-player gateway and disposable test session are used. **No
canonical story import, HTTP exposure or production permission.**

| ID | Deliverable | Dependencies | Classification | Status | Acceptance |
|---|---|---|---|---|---|
| PLAY-01a | Player-only, read-only JSON narrative handoff | Verified PlayerGateway / SQLite, no health dependency | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | Only scene + player's own RPG status + player's recorded memory, coherent revision; never raw WorldState/NPC ledger |
| PLAY-01b | Local temporary demo `scene` and `handoff` commands | PLAY-01a; existing demo | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | Read-only, no character auto-decision, no hidden nearby NPC beliefs; command IDs unaffected |
| PLAY-01c | Disposable resumable demo `scene` and `handoff` commands | PLAY-01a; backup P0 gate stays open | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | Does not create a new checkpoint / advance time; fresh restart yields consistent safe projection |
| PLAY-01d | NPC, end-to-end CLI, privacy, save/replay tests | PLAY-01a–c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | Nora/Basim/remote Sara, travel, look, wait, forged input; dual Python 3.10/3.13 entire workflow green on final SHA |

This batch is an **offline playable vertical-slice improvement**, not an
implementation or closure of the physical symptom subphase. Verify end-to-end
CI at the final commit before declaring anything `CLOSED_TECHNICALLY`.


## BATCH-PLAY-01 — Technical closure verified (2026-11-07)

**Accepted code SHA:** `45b876f237fac483842e702bf9c5dd6fb4f81ab8`.
**Exact-SHA full GitHub Actions:** [run 42316561009](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42316561009) —
Python 3.10 SUCCESS and Python 3.13 SUCCESS, including the CLI subprocesses,
the 7-NPC privacy scene, independent local evidence, read-only handoff,
SQLite resume/replay, and regression/parity gates.

- `PLAY-01a` `CLOSED_TECHNICALLY`: `player_handoff()` emits a
  JSON-compatible scene/status/memory envelope solely from the player's
  trusted `PlayerGateway`. Rejects `WorldState`/plain dicts, refuses
  mismatched revisions, exposes no remote facts or other NPC clinical data.
- `PLAY-01b` `CLOSED_TECHNICALLY`: `scene` and `handoff` work in
  the existing offline temporary CLI without moving Carlos, writing an
  observation, advancing time or changing command IDs.
- `PLAY-01c` `CLOSED_TECHNICALLY`: identical functionality in the
  existing opt-in **disposable** resumable demo. No new checkpoint on a
  read-only command, no bypass of `--disposable-test` or backup P0.
- `PLAY-01d` `CLOSED_TECHNICALLY`: end-to-end tests exercise
  Carlos, Nora, Basim, Sara, Adel, Salma, Huda and Omar as independent
  actors, reject remote interaction with Huda and ensure the player's
  remembered observation excludes remote NPCs and private injury data.
  The real CLI parser's `carlos> ` prompt prefix is handled explicitly.
- User-facing invocation instructions: [PLAYABLE_BATCH_01_GUIDE.md](PLAYABLE_BATCH_01_GUIDE.md).
- This is an incremental **offline playable test slice**, not the complete
  Carlos story, automatic narration, external authentication, a production
  save, or a medical symptom source. `03-A7c` and `03-A` remain OPEN,
  `P0_PRODUCTION_NOT_APPROVED`, independent review deferred by owner.
  No Schema/Rules version bump, `main` merge or original story edits.


## PLAY-02 — seven-NPC autonomous offline scene (2026-11-07)

Batch analysis/plan before code, independent of the blocked 03-A7c physical
symptom source. **Priority: a playable living test-world instead of more
isolated engine services.** No change to the canonical Carlos story.

| ID | Scope | Dependencies | Classification | Initial status | Acceptance |
|---|---|---|---|---|---|
| PLAY-02a | Trusted disposable multi-location 7-NPC + Carlos setup with initialized action counters | Schema32/Rules42 and existing player gateway | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | Seven named NPCs, actual roads and simulated travel; no invented private NPC memory, no unbacked stock |
| PLAY-02b | Explicit wait advances self-directed NPC schedules while Carlos remains player-controlled | PLAY-02a + LivingWorldEngine | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | At least two NPC actions progress, player never auto-acts, atomic event replay and deterministic time |
| PLAY-02c | New self-contained local living-world CLI with scene, look, status, remember, handoff, talk, move, wait | PLAY-02a–b, PLAY-01a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | No model API, no automatic world-time progress while paused; player-only handoff |
| PLAY-02d | Multi-NPC integration tests including forbidden remote talk, travel, privacy, NPC autonomy, replay, and real CLI subprocess | PLAY-02a–c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | Full final-SHA Python 3.10/3.13 CI success; no default fixture changes |
| PLAY-02e | Human-readable Windows trial guide and safety limits | PLAY-02c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY | Clear run commands, explicitly disposable, P0 unchanged |

**Dependency gates:** all PLAY-02 tasks are independent of 03-A7c medical
symptom provenance; do not change `main` or `AGENTS.md` here. Gate closure
on the exact final SHA, not an earlier green test run. Distinguish NPC
autonomy from narrative authorship: only actual engine events advance
the characters and the human decides Carlos's actions.

## PLAY-02 — closure of disposable autonomous village batch (2026-11-07)

**Five tasks `PLAY-02a`–`PLAY-02e` `CLOSED_TECHNICALLY`, code SHA
`898bb448b7b6d25585df45b1a13e6a53efa78b97`.**
Verified in [full GitHub Actions 42317917984](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42317917984):
**1,218 passed on Python 3.10 and 1,218 passed on Python 3.13**;
both matrix jobs SUCCESS. Full CI includes historic version/parity gates.

- PLAY-02a: fresh, trusted, isolated, non-canonical local world with Carlos,
  seven autonomous NPCs (Basim, Salma, Adel, Nora, Huda, Omar, Layla),
  three sites, timed actual roads, only explicitly initialized abstract
  action counters, and demonstrative RPG profile.
- PLAY-02b: `PlayerGateway` drives `LivingWorldEngine` with opt-in
  NPC navigation and local social autonomy when **Carlos's human chooses**
  `wait`. NPCs can work/rest/travel independently; Carlos is never given
  an autonomous NPC planner and elapsed world time never runs in background.
- PLAY-02c: `play_living_village.py` presents `scene`, `look`,
  `status`, `remember`, `handoff`, `move`, `talk` and `wait` in an
  offline disposable terminal session. Player-only handoff remains factual
  and cannot expose remote characters or NPC private medical/intent data.
- PLAY-02d: seven integration tests verify physical road time, lack of
  teleportation, player ownership, independent decisions, remote-talk
  rejection, exact SQLite snapshot/reopening, deterministic two-file
  simulation and real subprocess interaction. All in the final SHA's
  1,218-test full regression.
- PLAY-02e: [Windows hands-on guide](PLAYABLE_BATCH_02_LIVING_VILLAGE.md)
  written, no API or provider connection required.

**Explicit limits:** disposable experiment only; temporary SQLite is
discarded when CLI exits. This is not original Carlos story import, nor
production P0 restore approval, nor a medical observable symptom source.
`03-A7c` / `03-A` remain OPEN, `EXTERNAL_REVIEW_DEFERRED_BY_OWNER`
and `P0_PRODUCTION_NOT_APPROVED`; `main` unchanged. No Schema or Rules
version changes. Any future batch must classify independent work first,
plan, execute, exercise NPC tests, and validate exact final SHA.

## PLAY-03 — resumable offline seven-NPC living village (planned 2026-11-07)

Owner-approved batch scheduling: analyze dependencies before implementation;
target an actual, restartable test-play loop, not a new medical symptom rule
or undocumented production approval. Existing exact-green baseline
`c541e4ee`, CI `42318425675` SUCCESS on both Python 3.10 and 3.13.
`03-A7c` remains OPEN. `main` and canonical story files are immutable.

| ID | Deliverable | Prerequisite | Classification | State / acceptance |
|---|---|---|---|---|
| PLAY-03a | Bind a *trusted same-session* NPC autonomous engine to `ResumableTestSession` | `PLAY-02`, `01-Z` | `CHAT_EXECUTABLE / CLOSED_TECHNICALLY`: refuse forged gateway, mismatched world/player/store/clock, closed session; no world writes |
| PLAY-03b | `play_living_resumable.py` local executable with `--new/--resume`, `--disposable-test`, explicit request IDs and immutable checkpoints | PLAY-03a | `CHAT_EXECUTABLE / CLOSED_TECHNICALLY`: actual seven-NPC simulation after restart, `scene/handoff/remember` read-only, repeat commands rejected, unknown args do not change world |
| PLAY-03c | Deterministic NPC + player multi-process smoke tests | PLAY-03a/b | `CHAT_EXECUTABLE / CLOSED_TECHNICALLY`: Basim/Nora/Salma/Adel/Huda/Omar/Layla, mid-player-travel, no remote speech, SQLite verify/reopen, duplicate IDs, unchanged logical time after shutdown |
| PLAY-03d | Fault/compatibility/authorization tests for new/resume/checkpoint | PLAY-03b | `CHAT_EXECUTABLE / CLOSED_TECHNICALLY`: reject missing disposable opt-in, wrong save, old version, mismatched checkpoint SHA, no overwrites/no accidental reset; retain P0 gate |
| PLAY-03e | Concise Windows copy/run/resume tutorial | PLAY-03b | `CHAT_EXECUTABLE / CLOSED_TECHNICALLY`: user can complete real stop/restart with no API; distinguish experimental save from production |
  
Acceptance: targeted scenarios and complete GitHub Actions matrix on **exact
final implementation SHA**, Python 3.10 and 3.13, with SQLite replay and
legacy parity gates; no invented success before the CI result. No dependency
on an unimplemented visible-injury producer. Every new durable change is
disposable-test only and must not silently allow production games.

## PLAY-03 — verified technical closure of restartable seven-NPC batch (2026-11-07)

All five tasks `PLAY-03a`–`PLAY-03e` are **CLOSED_TECHNICALLY**
on exact tested SHA `e9706feda7d9c948e0f86599f60874d2284aafdb`.
GitHub Actions [run 42326538567](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42326538567) is
**SUCCESS in both Python 3.10 and 3.13** — `1,230 passed`
in each; full workflow also checks backwards compatibility and semantic
parity.

- PLAY-03a: `ResumableTestSession.bind_gateway()` accepts only a
  `PlayerGateway` bound to the identical active store, clock, world
  and human player; rejects foreign identities and closed sessions.
  Binding is read-only and retains the preexisting P0 test-only gate.
- PLAY-03b: new `play_living_resumable.py` can create/resume the seven-NPC
  living village. NPCs continue deterministic action/travel only during
  a human-triggered wait; persisted command IDs prevent double actions.
  A valid matching checkpoint at the saved revision is mandatory on
  resume; new worlds reject existing same-prefix backup folders.
- PLAY-03c: subprocess tests across actual separate Python processes
  verify persistent memories, NPC schedules, Carlos's mid-route timing,
  seven independent characters, no out-of-session simulation time,
  and exact SQLite replay.
- PLAY-03d: tests reject missing `--disposable-test`, invalid commit
  shapes, missing backup folder/checkpoint, corrupt manifests, mismatched
  commit provenance, stale database version, existing file overwrite,
  forged gateway, and duplicate request IDs; failures leave saved world
  intact.
- PLAY-03e: user-ready Windows/PowerShell
  [instructions](PLAYABLE_BATCH_03_RESUME.md) cover explicit create,
  `id` commands, safe reading, quit and subsequent resume.
- `main` and original Carlos story unmodified, Schema 32 / Rules 42
  unchanged, **no API connection** and no background time. The new saved
  world is **experimental and disposable-test only**, not an approved
  canonical save. `P0_PRODUCTION_NOT_APPROVED` and
  `EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain. `03-A7c` physical
  symptom source and parent `03-A` still OPEN.

This closure records the verified code SHA; the commit containing the
documentation-only status update needs its own CI observation if exact-HEAD
status is later requested. Do not equate this technical closure with
production restoration authorization.

## PLAY-04 — current player-visible NPC activity scene (planned 2026-11-07)

Analysis: PLAY-03 saves and continues a living village, but `scene` and
`handoff` currently show only occupants and roads: Carlos cannot see
nearby NPCs **doing** anything. A safe incremental slice is read-only
current visible behavior, not guessed motives, medical signs, diagnoses,
secret tasks or a retrospective observation memory. No new event, schema
migration, auto-player or unapproved production save is needed.

| Task | Scope | Dependency | Route | Status |
|---|---|---|---|---|
| PLAY-04a | Pure `WorldState`-only co-located visible-activity projector for running rest/work/forage and real local production | Existing validated event-sourced actions, movement and production | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-04b | Wire bounded output to `PlayerGateway.inspect` and hence `player_handoff` (only when player physically present; no change to player-in-transit view) | PLAY-04a, PLAY-01 | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-04c | Multi-person adversarial and lifecycle tests: Carlos, Nora, Basim, Adel, Salma, Huda, Omar, Layla; remote privacy, no diagnoses, current only, exact due tick, replay and SQLite reopen | PLAY-04a/b | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-04d | Real local AND resumable CLI / JSON handoff regressions and read-only idempotence | PLAY-04b, PLAY-02/03 | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-04e | Instructions clarifying a visible action does not establish motivation, cause, past knowledge or medical symptoms | PLAY-04b | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

Conservative visibility rules: player physically co-located **now**, NPC
not traveling, action truly running at current logical tick; expose
`actor_id` and bounded activity label **only**. Never emit private
needs, goals, injury, duration/due time, job recipe, wages, stock, action
ID or NPC knowledge. Deliberate `look` still records identity only;
`scene` is a read-only **current** projection, not persistent witnessing.
During travel, no scene activities. Preserve previous saved worlds and
existing `PlayerObserved` event contract: Schema32/Rules42 unchanged.
Tests on exact final code SHA must succeed in Python 3.10 and 3.13.

Note: `03-A7c` physical injury symptom producer remains blocked and
is **not** implemented or completed by these activity labels; `main`
and canonical story stay untouched, P0 production unapproved.

## PLAY-04 — verified technical closure of current visible NPC activities (2026-11-07)

**All five tasks `PLAY-04a`–`PLAY-04e` CLOSED_TECHNICALLY**
at exact code SHA `35d963c0d21c3265ac6704aa4d7016a00dc9f514`.
GitHub Actions [run 42328003868](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42328003868)
**SUCCESS**: **1,240 passed on Python 3.10** and **1,240 passed on Python
3.13**, including historic version/parity and all new NPC integration tests.

- PLAY-04a: pure `visible_player_activities` accepts a validated
  `WorldState` and real player ID. It projects only **current
  co-located, nontravelling, actually running** `rest`, `work`,
  `forage` or a genuine funded production job as the bounded labels
  `resting/working/foraging/producing`. Nothing is inferred from private
  injuries, intentions, profession alone or merely scheduled future work.
- PLAY-04b: `PlayerGateway.inspect` includes `activities` only in
  `present` scenes. A travelling Carlos receives the original
  route/remaining-time view, with **no** remote activity data.
  `player_handoff` carries the same bounded present observation and
  remains revision-coherent, without a new event or command.
- PLAY-04c: independent seven-NPC observations exercise Basim working,
  Nora resting with/without a private injury, Adel/Salma/Huda/Omar/Layla
  isolation, a physical bakery production job, actual seven-NPC
  foraging, exact activity completion tick, SQLite snapshot/reopen,
  and denial of forged world/nonplayer input.
- PLAY-04d: real local and resume CLI subprocesses confirm new activity
  visibility, unchanged time/memory/revision from repeated
  `scene/handoff`, persisted activity through safe SQLite reopen and
  unchanged checkpoint counts. Earlier intermediate CI failures came
  exclusively from the test harness writing literal `\\n` instead of
  actual command separators; corrected prior to verified green SHA.
- PLAY-04e: see
  [PLAYABLE_BATCH_04_VISIBLE_ACTIVITY.md](PLAYABLE_BATCH_04_VISIBLE_ACTIVITY.md)
  for the distinction between **current visibility** and **durable
  player memory**. `look` still records only nearby identities;
  don't invent past actions in `remember`.

**Explicit boundaries:** `03-A7c` and `03-A` remain OPEN; a visible
rest is not a medical symptom or diagnosis and no trusted physical
wound/limp producer is implemented. `P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain. Schema 32, Rules 42;
no migration, `main` merge or canonical story modification.
This closing documentation commit is subsequent to the independently
verified code SHA and has its own CI status.

## PLAY-05 — Player market purchasing and personal supply ledger (planned 2026-11-07)

**Analysis before implementation:** Local NPC market already has posted offers,
finite stock, trusted price matching, exact recorded transfers and durable
event replay. Carlos presently cannot buy; player-only RPG `inventory` domain
is intentionally unimplemented. Scope this batch strictly to **initialized
entity-owned resource balances** for Carlos, never fabricate RPG equipment or
allow a player to spend an NPC's funds.

| Task | Scope and strict dependency | Route | State |
|---|---|---|---|
| PLAY-05a | Extend validated MarketTradeExecuted for a physically present human buyer, and preserve existing NPC seller/stock ownership and conservation; existing NPCMarketService.buy must stay NPC-only | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-05b | Trusted `PlayerGateway.offers`, `supplies`, and `buy`: only local public quote, own initialized balances, bounded quantity/price, no in-transit exchange, exact revision and dedup ID | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-05c | Add a small finite bread-and-copper test market to disposable seven-NPC fixture, clearly marked as demo setup; `offers/supplies/buy` in both temporary and restartable CLIs | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-05d | Integration/adversarial NPC and player tests: Basim/Salma seller/local witness, Nora/Huda remote isolation, inventory conservation, price bait, stock depletion, busy/stale/travel/duplicate/replay/reopen | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-05e | Windows guide: identify distinct entity-owned resources vs unimplemented RPG inventory; exact CI matrix on final code SHA and no parent-phase premature closure | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Security:** A purchased resource is real on `state.resources[carlos]`, NOT
yet `rpg_profiles[carlos].inventory`. No user-supplied actor identity on
PlayerGateway buys, no unofficial HTTP client exposure; NPCMarketService
must not gain the right to purchase as a human. A trade cannot be remote
or during physical travel, needs a present/unoccupied real seller and
initialized buyer pay/goods balances. Any input failure or stale
command rejects without changing state. No schema migration, main merge,
original story import, medical symptom producer, automatic currency minting,
production P0 authorization or background play. Full GitHub Actions
Python 3.10 + 3.13 required at exact code SHA to close tasks.

## PLAY-05 — verified technical closure of Carlos's finite market purchases (2026-11-07)

All five owner-approved tasks `PLAY-05a`–`PLAY-05e`
**CLOSED_TECHNICALLY** at exact code SHA
`d3e90f68f68b5a376bf976a866649ac6e1ca12f8`.
GitHub Actions [run 42329804953](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42329804953):
**1,262 passed on Python 3.10 and 1,262 passed on Python 3.13**,
both jobs SUCCESS including all historic parity and regression gates.

- PLAY-05a: `MarketTradeExecuted` now supports a human-controlled buyer
  only when physically present, not in transit and backed by an exact
  authorized local purchase. All offers remain NPC-posted and backed by
  finite real owner stock; ledger validation permits real player buyers
  without weakening transfer conservation. `NPCMarketService.buy` is
  explicitly still NPC-only; human orders go through `PlayerGateway`.
- PLAY-05b: new `PlayerGateway.supplies`, `offers` and `buy` project
  only Carlos's known owned resource balances, actionable **local**
  public quotes, and trusted price-locked transactions. Exact revisions,
  bounded inputs and durable command IDs reject double spends or stale
  orders. `player_handoff` now includes bounded `player_supplies`
  with the same revision, not an NPC's wallet or secret inventory.
- PLAY-05c: **opt-in disposable** `setup_living_market_world` adds Salma
  with 3 own bread, 0 copper, Carlos with 10 copper, 0 bread and an
  NPC-posted 2-copper bread quote. In-world trade conserves exactly
  3 loaves and 10 copper; the original bare seven-NPC fixture remains
  unchanged. Both living CLI variants implement `offers`, `supplies`
  and `buy` with a checkpoint only after successful mutations.
- PLAY-05d: independent NPC/player tests exercise Salma busy, Basim
  co-location, Nora/Huda/Omar/Layla remote secrecy, invalid or changed
  price/quantity, overselling, denied NPC-service impersonation,
  no untrusted event capability, player travel, stale revision,
  repeated request IDs, SQLite snapshot/reopen and real two-process
  CLI stop/resume. All pass on the accepted code SHA.
- PLAY-05e: Windows tutorial and strict ownership distinction documented
  in [PLAYABLE_BATCH_05_MARKET.md](PLAYABLE_BATCH_05_MARKET.md).
  Earlier intermediary CI had a **test-only** failure expecting
  a Python dict repr in the CLI receipt instead of `total_paid: 4`;
  fixed in the exact green SHA and no accounting bug established.

**Limits remain:** `state.resources[carlos]` is a resource owner ledger,
not the unimplemented RPG `inventory` or `equipment`. Do not
fabricate combat, food consumption by player, experience points, items
or money outside initialized source/atomic transfers.
`03-A7c` and parent `03-A` remain OPEN, physical medical sign source
blocked, `P0_PRODUCTION_NOT_APPROVED`,
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER`. No Schema/Rules bump,
canonical story mutation, `main` merge, remote API or unattended play.
This closure documentation commit is subsequent to the accepted green
code SHA and may have its own CI run.

## PLAY-06 — Player-owned market receipts (2026-11-07)

**Analysis before implementation:** PLAY-05's existing MarketTradeExecuted
ledger persists real trades with trusted buyer identity, price and resource
conservation. A bounded read-only projection makes Carlos's own purchases
visible across travel, save/reopen and narrator handoff. This does not depend
on the blocked medical observation producer or production P0.

| Task | Dependency and scope | Route | State |
|---|---|---|---|
| PLAY-06a | PLAY-05 green SHA; player-only bounded receipts | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-06b | PLAY-06a; coherent handoff includes five own receipts | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-06c | PLAY-06a; temporary/restartable CLI purchases command | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-06d | PLAY-06a–c; Basim trade privacy, Carlos travel/duplicate, readonly, adversarial limits, replay/reopen, CLI tests | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-06e | PLAY-06a–d; guide, final SHA/dual-Python CI and technical closure | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Acceptance:** exact final code SHA must pass full Python 3.10/3.13 matrix.
Do not expose other buyers, NPC balance ledgers or private before/after
numbers; don't create resources, read-side events or checkpoints. No
schema/rules bump, original story change or main merge. 03-A7c/03-A, P0 and
independent-review gates remain open. Don't declare closure without CI proof.

Verification branch: simulation-engine-phase-play-06-receipts (triggers the
full matrix on push). This task remains open until its exact run is checked.

### PLAY-06 technical closure (2026-11-07)

All five tasks PLAY-06a–PLAY-06e are CLOSED_TECHNICALLY.
The full dual-Python suite passed on **exact code-and-test SHA**
25fdbf5e30dd23f0471d4287cfa7585a47484545 in
[Actions run 42352820512](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42352820512):
**1,270 passed on Python 3.10** and **1,270 passed on Python 3.13**.
Both matrix jobs ended in SUCCESS, with compileall, regression, parity,
historic baselines, SQLite/replay and scenario smoke checks green.

Eight additional PLAY-06 tests include real Basim NPC buying before Carlos,
private receipt filtering, fraud rejection, player travel visibility, no
read-side mutation, mixed-revision handoff detection, SQLite snapshot/reopen,
temporary CLI, and checkpoint-preserving two-process resumable CLI.

The history carries **only owned player receipts** (up to 20, most recent
five in handoff); it neither fabricates goods nor exposes the full NPC market
ledger. Schema 32 / Rules 42 unchanged. This documentation-only closure
commit follows the tested SHA and is not a claim of new post-commit CI.
Parent 03-A/03-A7c still OPEN, external review deferred, production P0
unapproved, and main/original story untouched.

## PLAY-07 — Player-to-NPC finite gifts and independently chosen receipt (2026-11-07)

**Preimplementation analysis:** A market trade already conserves finite resources,
but NPC assistance is NPC-to-NPC and a social `offer_help` is only speech, not
a transfer. Therefore using either as a player gift would misstate ownership.
A new `PlayerGiftDelivered` reducer and dedicated durable gift_authorized
command capability are required, with Schema 33 / Rules 43 explicit versioning.
A nearby NPC's existing deterministic acceptance of help offers controls
whether the gift can complete; no automatic gratitude, hunger relief or RPG XP.
This batch depends on PLAY-06 green SHA and is independent of 03-A7c/P0.

| Task | Scope and prerequisites | Route | Status |
|---|---|---|---|
| PLAY-07a | New atomic conserved gift event, separate recorded authorization and replay; based on PLAY-06 | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-07b | Trusted player-bound give command with exact revision and dedup ID; depends on 07a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-07c | CLI give in temporary/restartable village; depends on 07b | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-07d | NPC behavior, privacy, attempts/forgery, conservation, duplicate, route/time and snapshot/reopen CLI tests; 07a–c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-07e | Windows guide and exact full dual-Python CI closure; depends on 07d | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Security/validation gates:** Python 3.10 and 3.13 full CI on final code SHA,
fixed balances for donor/recipient, deny NPC impersonation and unauthorized
replay, no hidden NPC inventory exposed and no new arbitrary legal authority.
Gift transfer is a deliberate player action only, never an automatic hunger
or medical cure. P0 production remains NOT_APPROVED; independent review deferred;
03-A7c and parent 03-A remain OPEN. Do not merge to main.

### PLAY-07 verified technical closure (2026-11-07)

PLAY-07a–PLAY-07e all **CLOSED_TECHNICALLY** against exact final
code-and-tests SHA `989cee8d21c4e91c917fb2d68b788cfd778bd0f4`.
[GitHub Actions run 42354191763](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42354191763)
is **SUCCESS** with **1,293 passed on Python 3.10** and
**1,293 passed on Python 3.13**. Both jobs also passed all existing smoke,
compatibility/parity, historical saved-world rejection and replay checks.

The first completed trial exposed 18 *test/CI-only outdated current-version
pins* (32/42); after investigating the precise failures, 22 targeted updates
in 16 tests/workflow files synchronized the active expected version to
Schema 33 / Rules 43 while retaining historical frozen-version assertions.
The final green SHA above is authoritative; earlier red SHA runs were not used
as proof. Dedicated SQLite gift authorization survives replay, rejected/remote
NPC gifts do not create resources, duplicates and stale commands are blocked,
and all original market/survival assertions remain green.

**Not approved for production:** P0_PRODUCTION_NOT_APPROVED.
**External review:** EXTERNAL_REVIEW_DEFERRED_BY_OWNER.
**Parent injuries:** 03-A7c and 03-A still OPEN; neither closed by this batch.
No main merge, original story mutation, player combat or player hunger logic.
This docs-only closure commit follows the verified test SHA and is not a
new code test result.


## PLAY-08 — Verified player gift history (planned 2026-11-07)

**Analysis before implementation:** PLAY-07 reliably transfers finite goods
and records an authorized \`PlayerGiftDelivered\` event, but the player cannot
review past delivered gifts after leaving the village. Unlike NPC gossip or
unaccepted offers, the player's own accepted gifts are firsthand history.
A bounded read-only projection of verified events requires no new schema or
event type and is independent of the open 03-A7c physical injury source.

| Task | Scope / dependency | Route | State |
|---|---|---|---|
| PLAY-08a | Verified event-only own gift receipts, max 20, newest-first; PLAY-07 | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-08b | Five owned receipts in revision-coherent narrator handoff; PLAY-08a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-08c | Read-only \`gifts\` in temporary and resumable CLIs; PLAY-08a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-08d | Tests for Basim/Nora/Salma privacy, rejected gifts, duplicate, tamper, SQLite reopen, two CLIs; PLAY-08a-c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-08e | Player guide, dual-Python exact-SHA CI and closure report; PLAY-08a-d | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

Security: only accepted events by the bound actual player, no internal NPC
balances or private state; no read-side command, checkpoint or time advancement.
A failed event integrity verification must fail closed. Schema 33 / Rules 43
unchanged. No \`main\` merge, canonical story modification, automatic NPC
gratitude, or production P0 authorization. Pending GitHub Actions verification
on Python 3.10 and 3.13; do not claim task closure yet.

### PLAY-08 verified technical closure (2026-11-07)

**PLAY-08a–PLAY-08e CLOSED_TECHNICALLY** at final code-and-test SHA
`7308cff7409f959221f62782c4ddc3b6491054c0`.
[GitHub Actions run 42355553139](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42355553139)
completed SUCCESS: **1,303 passed on Python 3.10 and 1,303 passed on Python 3.13**,
including all existing compatibility, replay, smoke and historical gates.
Ten additional PLAY-08 tests cover bounded empty history, exact delivered gifts,
same-tick receipts, failed/duplicate/travel attempts, player-bound identity,
revision-coherent handoff, event tamper rejection, SQLite snapshot/reopen,
and temporary plus two-process resumable CLI behavior.

An initial CI run on `fdc10e46` failed on a **CLI indentation syntax error**.
This was fixed on the exact verified SHA above; no earlier failing run was
used as closure evidence. Read-only gifts do not mutate the world, create
resources, add medical facts, or interpret NPC gratitude. Schema 33 and Rules
43 unchanged, no new migration or outside authorization.

This documentation-only technical-closure commit succeeds the verified code SHA
and must not be described as having passed the cited earlier CI itself.
`03-A7c` and `03-A` remain OPEN; `P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain. No change to `main` or
canonical Carlos story files.


## PLAY-09 — Real player-to-NPC conversation journal (planned 2026-11-07)

**Analysis before implementation:** The player's local social speech and
NPC's deterministic recorded reaction already form a durable social-message
ledger. The narrator currently receives no read-only history of those
conversations, so it risks inventing dialogue continuity after travel or
restart. A verified, player-bound event projection is independent of the
blocked 03-A7c medical symptom source and requires no schema/rules change.

| Task | Scope and dependency | Route | Status |
|---|---|---|---|
| PLAY-09a | Player-owned, received-only conversation history, ordered by event sequence, max 20; PLAY-08 green | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-09b | Revision-consistent narrator handoff: last five authentic conversations; PLAY-09a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-09c | \`conversations\` read-only command on both disposable CLIs; PLAY-09a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-09d | NPC privacy/independent reactions/invalid attempts/duplicates/travel/tamper/reopen and CLI tests; PLAY-09a-c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-09e | Guide and exact-SHA dual-Python full CI technical closure; PLAY-09d | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Guardrails:** No invented NPC dialogue or objective trust report; only
the player's own authored text and proven reaction categories. No raw NPC
message ledger, hidden NPC motives, hearsay reclassification, speculative
knowledge, new world events or read-side checkpoints. State.revision must
match verified replay; store gate remains local and trusted (P0 OPEN).
Schema 33 / Rules 43, 03-A7c/03-A OPEN, external review deferred.
No \`main\` merge or canonical story modifications. Dual-Python CI verified on the exact code SHA below.

### PLAY-09 verified technical closure (2026-11-07)

All five tasks PLAY-09a–PLAY-09e are **CLOSED_TECHNICALLY** at the exact
code-and-test SHA `40ea48770e5daec6cb81ce406a302dd0f0fd6dd9`.
[GitHub Actions 42356386832](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42356386832)
concluded **SUCCESS**: **1,316 passed on Python 3.10** and **1,316 passed
on Python 3.13**, including the comprehensive historical parity, replay,
saved-world compatibility, CLI smoke and integration gates.

Thirteen new PLAY-09 tests cover Basim/Salma/Adel recorded reactions; remote
Nora/Huda/Omar/Layla isolation; duplicates, invalid speech, same-tick order,
stale/mixed-revision handoff rejection, command privacy, travel, tamper
rejection, SQLite snapshot/reopen, and both temporary/resumable real CLIs.

Only player-authored delivered text and the NPC's recorded response **category**
are exposed. No NPC dialogue is fabricated; no NPC private trust, hidden
motives, third-party messages, resources or game-world time change due to
reading history. Schema 33 / Rules 43 unchanged, no migrations.

The documentation-only closure commit follows the **verified code SHA** and
is not represented by the same CI check. Phase 03-A7c/03-A remain OPEN;
`P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain unchanged. No `main` merge
or canonical story changes.


## PLAY-10 — Player asks NPC about an evidenced food location (planned 2026-11-07)

**Analysis before implementation:** PLAY-09 records actual social speech, while
01-T/01-X already provide NPC-local food observations and replay-safe player
hearsay. A trusted one-command interaction can combine the existing
\`request_help\` reaction with an NPC's own evidenced belief, *only when* the
character's independent response is \`considered\`. This does not invent
dialogue, update medical observation contracts, or depend on P0 production.
A finite test-only food fixture creates observable evidence, not free player food.

| Task | Scope / dependency | Route | Status |
|---|---|---|---|
| PLAY-10a | Atomic player question and conditional NPC response using existing social + hearsay events; PLAY-09 green | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-10b | Seed truly initialized local \`wild_food\` and valid Basim/Omar sightings in isolated market demo only; 10a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-10c | \`askfood <npc> <site>\` in disposable temporary and resumable CLI; 10a | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-10d | NPC independent choices, privacy, nonexistent/remote/unknown claims, dedup, forged hearing, replay and save tests; 10a–c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-10e | Guide, full exact-SHA Python 3.10 + 3.13 matrix and closure; 10a–d | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Security/causality:** A valid site name alone provides zero world truth.
NPC's own known fact, proper direct or non-instantly re-shared source, and
pre-request willingness must all hold. No change to schema 33/rules 43,
no RPG inventory/XP, no narrator omniscience, no hidden needs/trust exposed,
no time advance from speech, no main/story edits. Open 03-A7c/03-A,
P0_PRODUCTION_NOT_APPROVED and EXTERNAL_REVIEW_DEFERRED_BY_OWNER remain.
All tasks require exact final code SHA dual-Python CI before technical closure.

### PLAY-10 verified technical closure (2026-11-07)

**PLAY-10a–PLAY-10e CLOSED_TECHNICALLY** at exact code-and-test SHA
`1b4d60c301be4c158f4405dad52515c9092ac616`. [GitHub Actions run 42357107282](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42357107282)
concluded **SUCCESS**, with **1,339 passed on Python 3.10** and
**1,339 passed on Python 3.13**. All existing smoke, historic compatibility,
semantic parity and SQLite/replay gates also succeeded. This increases the
prior accepted suite of 1,316 tests by 23 parameterized PLAY-10 cases.

- A player-only `ask_food` executes one atomic `request_help` social exchange.
  The NPC's independent, prior-trust reaction determines whether its own
  direct or valid non-instantly relayed food belief is voluntarily shared.
- Only `unverified` hearsay is delivered into the player's durable memory;
  the narrator never receives remote resource totals, NPC hidden beliefs,
  goals, numerical trust or fabricated NPC speech.
- The opt-in disposable market fixture has exact finite square/woods food
  stocks (2 and 4) and two witnessed observations by physically present
  Basim/Omar; Salma has no inferred food memory. No resources are granted
  to Carlos or automatically consumed.
- Both real disposable CLIs implement `askfood <npc> <site>`, with
  explicit command-ID deduplication and restartable checkpoints.
- Tests cover voluntary refusal after a threat, several independent
  characters, co-location, knowledge boundaries, malformed input,
  failed/stale/duplicate operations, tampered provenance, SQLite
  snapshot/reopen and two-process CLI resume.

**Scope limitations:** Schema 33 / Rules 43 unchanged. No `main` merge,
canonical story mutation, extra player RPG powers or network authorization.
`03-A7c` and `03-A` remain **OPEN**; `P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain. The documentation-only closure
commit follows the tested SHA and is not itself the quoted code CI run.


## PLAY-11 — Physically local food survey and finite pickup (2026-11-07)

**Analysis before implementation:** PLAY-10 made food beliefs meaningful but
Carlos could not physically validate a claim or collect existing natural food.
The pre-existing NPC investigation/gathering event is NOT a player action.
PLAY-11 adds qualitative on-site survey and a player-bound one-unit pickup
of visible finite `wild_food` into explicitly initialized owner `food`.
The gateway groups a local player observation and pickup in one atomic
SQLite command; no hidden NPC inventory, hunger cure, XP, or food minting.
The new persisted event requires Schema **34** / Rules **44**. Independent of
03-A7c and production P0.

| Task | Scope and dependency | Route | State |
|---|---|---|---|
| PLAY-11a | Existing PLAY-10 green; present-only, qualitative local food check | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11b | One-unit PlayerFoodCollected reducer, active local player and source conservation | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11c | Opt-in fixture initializes player food=0, leaves older fixtures untouched | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11d | CLI checkfood/forage and revision-coherent narrator handoff | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11e | Many-NPC, anti-remote, anti-forgery, conservation, SQLite and two-CLI tests | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11f | User guide and exact-SHA full dual-Python CI, compatibility version pins | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Limits:** visible, immediately pickable food only; timed searching/hunting
and player hunger relief are NOT implemented. No natural regeneration,
automatic player actions, remote location knowledge or RPG inventory.
No main merge or original story mutation. `03-A7c` / `03-A` OPEN;
`P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain. Do not close until exact
code SHA passes full Python 3.10 + 3.13 matrix.

### PLAY-11 verified technical closure (2026-11-07)

All six PLAY-11a–PLAY-11f tasks **CLOSED_TECHNICALLY** on exact final
code-and-test SHA `ed1385f8c18123498a534b101ad268331eac9fbb`.
[GitHub Actions run 42361210471](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42361210471)
finished **SUCCESS**, with **1,356 passed on Python 3.10** and **1,356 passed
on Python 3.13**. Compile, historical rules parity, prior saved-world
rejection, CLI, snapshot/reopen and integrity gates all passed.

The new `checkfood` action reveals only a qualitative on-site deposit;
`forage` groups an authorized player observation with exactly one
`PlayerFoodCollected` event, transferring one initialized natural food
unit from the player's physical location to its initialized own `food`
balance, atomically. There is no time cost, player hunger/health effect,
regrowth, XP or automatic RPG inventory mapping. Remote site stock, private
NPC resources and unknown balances remain inaccessible.

The source-conserving reducer is replay-safe. Dedicated acceptance tests
cover live Basim/Salma/Omar/Adel/Nora/Huda NPC coexistence, remote/false
actor/quantity rejection, missing deposits, depleted stock, travel time,
duplicate/stale commands, active-session/action capability, local observation
precondition, SQLite snapshots and both real CLIs across process restart.

Initial CI run 42360856576 on `3f19531d` **FAILED**: test expectations
still pinned to Schema 33 / Rules 43 and both CLI bootstraps referenced an
old fixture name. These were repaired across 18 files. No failing run was
used as closure evidence. The accepted tested SHA above uses **Schema 34 /
Rules 44**, and updates only *current* version assertions: all frozen
historical compatibility gates remain.

**Open:** `03-A7c`, parent `03-A`,
`P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER`. No `main` merge or canonical story
edits. The following documentation-only closure commit is distinct from
the exact tested code SHA; it is not claimed CI-verified by that run.


## PLAY-12 — Timed, source-competitive player forage (2026-11-07)

**Analysis before implementation:** PLAY-11's immediate \`forage\` does not let
the village live or its finite food supply change while Carlos works.
Reuse the existing trusted \`ScheduledEventCreated\` / \`ScheduledEventFired\`
mechanism with a reserved \`__player_forage\` payload. A verified 60-second
due signal physically checks remaining local food *at completion* and
transfers at most one unit; another real actor may take the last unit first.
No time/event writes happen in the background. This changes event semantics:
**Schema 34 unchanged, Rules 45** (old Rules 44 save rejected).
No independent production/medical phase is touched.

| Task | Dependency / result | Route | State |
|---|---|---|---|
| PLAY-12a | PLAY-11 green; start a genuine 60-second bounded scheduled activity | CHAT_EXECUTABLE | VERIFICATION_PENDING |
| PLAY-12b | Due-tick conservation and no-reward depletion; no instant pickup loophole | CHAT_EXECUTABLE | VERIFICATION_PENDING |
| PLAY-12c | Busy-player constraints; allow only waiting, reading own view and snapshot/resume | CHAT_EXECUTABLE | VERIFICATION_PENDING |
| PLAY-12d | Both real CLI workflows and coherent narrator-facing activity/results; 12a-c | CHAT_EXECUTABLE | VERIFICATION_PENDING |
| PLAY-12e | Independent NPC time, multiple player competition, forged schedules, stale IDs, SQLite replay and adversarial tests; 12a-d | CHAT_EXECUTABLE | VERIFICATION_PENDING |
| PLAY-12f | Guide, current-rules compatibility assertions, exact-code-SHA dual Python CI and technical close; 12e | CHAT_EXECUTABLE | VERIFICATION_PENDING |

**Safety constraints:** No automatic player decisions, real-time offline progress,
unknown or remote resources, instant harvest, medical effects or RPG inventory
conjuring. At the due moment, insufficient stock means **depleted**, no minted
reward. Only a real human-controlled actor present throughout may start;
\`move\`, \`give\`, \`buy\`, \`talk\`, \`askfood\`, \`look\` and another \`forage\`
are denied during the timed action; \`wait\` advances NPC autonomous activity.
A separately authorized player action cannot cancel or prematurely fire the
reserved schedule. \`03-A7c\` / \`03-A\` remain OPEN, P0_PRODUCTION_NOT_APPROVED,
EXTERNAL_REVIEW_DEFERRED_BY_OWNER. No \`main\` merge/story edits.
