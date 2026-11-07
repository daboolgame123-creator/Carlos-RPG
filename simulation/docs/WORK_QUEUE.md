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
