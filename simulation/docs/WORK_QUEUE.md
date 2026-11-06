# Carlos RPG — سجل توجيه الأعمال القابلة للاستئناف

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
