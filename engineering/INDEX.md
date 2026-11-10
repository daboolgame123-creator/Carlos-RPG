# Carlos RPG — سجل الخطتين الهندسيتين قبل PLAY-48

## الدفعة التالية المثبتة — 10 نوفمبر 2026 (نتائج GitHub الفعلية)

- **CI-03b — قياس 6h/24h:** [تقرير العالم الحقيقي](reports/CI_03B_REAL_24H_HOTSPOTS_2026-11-10.md)؛ [Run #42787883806](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42787883806) **SUCCESS على Python 3.10/3.13**. الأحداث الجديدة 2,416 مقابل 10,000 `apply_event` call في 24h؛ إعادة الإسقاط/التحميل والتجميد مواضع كلفة مثبتة. `BOUNDED_24H_PROFILE_VERIFIED`؛ ليس إثباتًا لسبب 7d بكامله.
- **MIG-02a — عقد ترحيل مُعطّل:** [وثيقة دلالة الأحداث](reports/MIG_02_SEMANTIC_CONTRACT_2026-11-10.md)، [JSON](contracts/migration_41_56_to_42_57.json)، [نتيجة التثبت](reports/MIG_02A_PINNED_CONTRACT_RUN_2026-11-10.md)؛ [Run #42788288670](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42788288670) **SUCCESS كلا الإصدارين**. 55 حقلًا و73 Event selector ثابتة بين 41/56 و42/57، لكن `migration_approved=false`. `MIG02A_CLOSED_TECHNICALLY / MIG02B_OPEN`.
- **CI-04 — تجربة تعديل غير مجدية:** [تقرير رفض ترقيع `_freeze`](reports/CI_04_FREEZE_AB_NO_GO_2026-11-10.md)؛ [Run #42788654884](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42788654884) **SUCCESS** من حيث مقارنة A/B وصحة تطابق العالم، لكن البديل أبطأ ~2.4–2.6%، لذا `NO_GO`. لم يُعدّل المحرك.
- **CI-01 — تصنيف تغييرات Git:** [تقرير 3 عينات تاريخية](reports/CI_01_PATH_CLASSIFICATION_PROOF_2026-11-10.md)؛ [Run #42789060820](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42789060820) **SUCCESS**. حدد docs engineering مقابل docs قرار إطلاق مقابل code؛ لم تُغيَّر triggers أو Required Checks. `CLASSIFIER_PROOF_VERIFIED / RELEASE_CHANGE_BLOCKED_BY_BRANCH_POLICY_403`.

**المهام الآمنة التالية:** `CI-01b` اختبار PR مختلط وقراءة Required Status Checks من جهة مالك صلاحيات، `MIG-02b` دراسة أحداث أصلية ذات عهدة/سوق/إنتاج، ثم تصميم `CI-04b` بنية Snapshot/Replay على فرع أداء منفصل إذا أمكن ضمان صدق التحقق. لا تحسين قسري، ولا ترحيل عالم حقيقي، ولا انطلاق PLAY-48 بسبب تقارير جرد. `main` ثابت و`P0_PRODUCTION_NOT_APPROVED` مستمر.

## تنفيذ دفعة الجرد والقياس — 10 نوفمبر 2026 (دليل فعلي)

- **CI-00 (جزئي مثبت):** [جرد 50 Workflow وقياسات ستة تشغيلات ناجحة](reports/CI_00_BASELINE_2026-11-10.md)؛ ما زال التحقق من Required Checks محجوبًا بصلاحية GitHub API (403)، ولذلك لا تغييرات بعد على Required Gates أو حذف ملفات. `IN_PROGRESS / BASELINE_VERIFIED`.
- **MIG-00 (تحليل المصدر مثبت):** [تدقيق الفرق الحقيقي 41/56 إلى 42/57](reports/MIG_00_41_56_TO_42_57_AUDIT.md). الحقول الأساسية ثابتة لكن عقود الإنتاج/السوق تغيرت؛ لا تحويل معتمد أو تلقائي. `IN_PROGRESS / SEMANTIC_INVENTORY_REQUIRED`.
- **MIG-01 (عينة نسخ قديم مثبتة):** [فحص أصلي لإصدار 41/56 على Python 3.10 و3.13](reports/MIG_01_ORIGINAL_BACKUP_SAMPLE_2026-11-10.md)، [Run 42786900040](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42786900040) **SUCCESS**، 5 اختبارات لكل Python تشمل WAL/restore/الرفض وعدم تعديل المصدر. **لم تحدث هجرة لإصدار 42/57**؛ بقية مهام MIG-01 وMIG-02 مفتوحة.
- **CI-03 (عينة فعلية مثبتة):** [41 اختبارًا + تجربة اقتصاد صغيرة على Python 3.10 و3.13 وتحليل cProfile](reports/CI_03_BOUNDED_PROFILE_2026-11-10.md)؛ [Run 42786344145](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42786344145) **SUCCESS** على SHA `d1b379b4c6c5ef4d8fe86a794501f2718939c4f2`. أظهر كثافة إعادة إسقاط الأحداث/التحميل؛ لم يثبت بعد اختناق تجربة الأيام السبعة. `BOUNDED_SAMPLE_VERIFIED`.
- **بيئة التنفيذ:** فرع `engineering/ci-mig-baseline-20261110` مستقل؛ لا تغييرات في `simulation/src/` أو `simulation/tests/` أو `main`، ولا تغيير Schema/Rules أو ترحيل ملف حفظ. قياس الأداء يستعمل [workflow محدود](../.github/workflows/ci03-performance-probe.yml) على الفرع الهندسي فقط، وليس بوابة نشر.
- **التتابع الصحيح:** `CI-03b` قياس 6h/24h، و`MIG-01` اختبار النسخة الأصلية، ثم تصميم `CI-01` بعد معرفة Required Checks أو تصعيد صلاحية القراءة، قبل أي CI-04 structural sharing. `P0_PRODUCTION_NOT_APPROVED` قائم.


**تاريخ الإيداع:** 2026-11-10  
**الحالة:** `PLANNED / NOT_IMPLEMENTED`، دون ترحيل حفظ أو تحسين CI مُنفذ.  
**الأساس المعتمد:** `feature/play47-npc-economic-endurance-20261109` / `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`، Schema **42** / Rules **57**. PLAY-47 **CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER** بعد تحقق [CI كامل](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42731120034) و[CI موجه](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42731103345) وترقية fast-forward. `main` خارج العمل، وP0 غير معتمد.

## الوثائق الأساسية

1. [SAVE_MIGRATION_PLAN.md](SAVE_MIGRATION_PLAN.md) — Migration صريح للحفظ مع مصادر إصدارات حقيقية، نسخة SQLite معزولة، توافق أحداث ومعانٍ، فشل آمن واختبارات استعادة.
2. [CI_PERFORMANCE_PLAN.md](CI_PERFORMANCE_PLAN.md) — قياس أسباب البطء، فصل Feedback السريع عن Release gate، تحسين الأداء من Profiling، ثم مراجعة Workflows بدون إسقاط اختبارات.
3. [سياسة التوافق الأصلية](../simulation/docs/SAVE_COMPATIBILITY_POLICY.md) و[EXTERNAL_VALIDATION_LEDGER.md](../simulation/docs/EXTERNAL_VALIDATION_LEDGER.md) هما مرجع الحفظ وP0؛ الخطتان لا تلغيان شروطهما.
4. [WORK_QUEUE.md](../simulation/docs/WORK_QUEUE.md) و[ROADMAP.md](../simulation/docs/ROADMAP.md) للتطوير المرحلي. لا تُفسّر حالة قديمة فيهما بدل فحص GitHub/قرار إغلاق PLAY-47 الفعلي.

## ترتيب التنفيذ المعتمد للتخطيط، لا التنفيذ

| الأولوية | المهام | ما الذي يسمح بها؟ | ما الذي لا تسمح به؟ |
| --- | --- | --- | --- |
| 1 | `CI-00` و`MIG-00` و`CI-03` — جرد وقياس | أعمال مستقلة على فرع مبني من SHA مغلق؛ قراءة الكود والسجلات دون تغيير حفظ لاعب | لا حذف workflows، لا تغيير نسخ مخطط البيانات، لا تجربة عالم حقيقي |
| 2 | `CI-01` ثم `CI-02` و`MIG-01` ثم `MIG-02` | نتائج جرد مؤكدة، سياسة GitHub Required Checks وقارئ إصدار قديم مثبت | لا رفع بوابات release ولا تجاهل اختلاف دلالة أحداث |
| 3 | `MIG-03` ثم `MIG-04`، وبالموازاة `CI-04` بعد `CI-03` | مسار تحويل قابل للإثبات + نسخة أصلية محفوظة، أو Profiling مثبت | لا كتابة على المصدر ولا optimizations تغيّر hash/replay |
| 4 | `MIG-05` و`CI-05` و`CI-06` | نجاح مصفوفة الفشل وإثبات تكافؤ النتائج قبل/بعد | لا وصف المراحل بأنها مغلقة قبل full exact-SHA |
| 5 | `MIG-06` — اعتماد جهاز/خادم فعلي | استعادة وrollback وWindows وصلاحيات وقرار مستقل وفق P0 | لا استيراد قصة أو اعتماد حفظ دائم قبل موافقة منفصلة |

**مبدأ الترتيب:** لا توجد تبعية تقنية تجعل PLAY-48، الخاصة بتكرار سلاسل الإنتاج داخل عوالم `disposable-test`، منتظرة لموافقة P0؛ لكن لا يجوز تحويل تلك العوالم إلى حفظ دائم أو إصدار إنتاجي. نفّذ أعمال البنية في فروع منفصلة ولا تخلط Schema/Rules أو تغييرات سرد القصة مع ميزة اللعب. تجنب تعطيل إصدار المحرك السليم أثناء بناء المهاجر.

## خطوات أي وكيل في المحادثة القادمة

1. اقرأ `AGENTS.md`، والملفين أعلاه، و`simulation/AGENTS.md`، ثم تحقق من حالة فرع التكامل وSHA/CI الحاليين. **لا تفترض أن وجود خطة يعني التنفيذ أو نجاح الاختبارات**.
2. احصر المهام الثلاث الأولى كدفعة جرد وقياس دون كتابة كود، ثم اختر التنفيذ الآمن التالي باعتمادياته. كل مهمة لها `PLANNED` أو `IN_PROGRESS` أو `BLOCKED` أو `CLOSED_TECHNICALLY` مع أدلة، وليس مجرد قائمة أمنيات.
3. عند البدء الفعلي، انقل السطر التشغيلي المناسب إلى `simulation/docs/WORK_QUEUE.md` ضمن PR التنفيذ، مرفقًا بالفرع وSHA والمقياس والـCI ومخاطر الرجوع؛ لا تنشئ حالة `DONE` من دون تنفيذ.
4. افصل كل PR عن الآخر: MIG للحفظ وCI للبنية، ولا تُقدّم تغييرات إلى `main` دون موافقة. لا تُلغِ Jobs موجودة لأن شكل الوثائق يوحي باختبار مستغنٍ عنه.
5. قبل أي دمج لميزة أو ترقية HEAD، تحقق من full 3.10/3.13 والبوابات المحددة على SHA النهائي؛ وثّق النتيجة وقارنها مع `38ef004` المرجعي. الشيفرة التي تغيّرها خطط الأداء قد تؤثر على الأحداث والتجزئات دون تغيير Schema؛ هذا يستدعي تدقيقًا دلاليًا صريحًا.
6. إذا بقيت بوابة خارجية (Windows/معدات/مراجع)، أضفها إلى [سجل التحقق الخارجي](../simulation/docs/EXTERNAL_VALIDATION_LEDGER.md) ولا تسمها ناجحة. كل طلب مهاجرة للعالم الحقيقي يتطلب إذنًا صريحًا.
7. بعد تنفيذ خطتي MIG/CI جزئيًا، قدّم جدولًا مختصرًا: الفرع، SHA، Schema/Rules، اختبارات 3.10/3.13، قياس زمن قبل/بعد، بوابات P0، وما بقي OPEN.

## لماذا لا يغيّر هذا الفرع PLAY-47؟

الأوراق هنا **توثيق تخطيط هندسي فقط**: لا تغيير في `simulation/src/` ولا اختبارات أو `.github/workflows/` أو Schema/Rules. لا يبدّل ذلك قرار إغلاق PLAY-47، ولا ينفذ PLAY-48، ولا يعني تشغيل migrations أو optimizations. بعد مراجعة وثائق الخطة يمكن ضمها للفرع المرجعي بعملية آمنة مع توثيق أثر CI؛ لا تمس `main` ولا ترفع بوابات P0.

**تعريف النجاح لهذه الدفعة:** ظهور وثيقتَي الخطة في GitHub، ووجود فهرس واضح ومرجع من `AGENTS.md` و`README.md`، والتحقق من SHA/الفروقات. هذا معيار **إيداع خطة** وليس نجاح تنفيذها.
