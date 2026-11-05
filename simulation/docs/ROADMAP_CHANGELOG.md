# سجل تغييرات خارطة الطريق — Carlos RPG

**الهدف:** إبقاء الخطة قابلة للتغيير مع الاحتفاظ بأسباب كل قرار. هذا سجل إدارة مشروع، **وليس** سجل أحداث عالم كارلوس.

## الصيغة المعتمدة

كل تغيير جديد يسجل: **التاريخ / المعرّف / مصدر الاقتراح / الدافع والدليل / البدائل / القرار / أثر التبعيات وSchema/Rules / حالة التنفيذ / وقت المراجعة التالية**. لا تُحذف الإدخالات السابقة؛ التصحيح يكون بمدخل جديد يشير إلى القرار المصحَّح.

### G-001 — 2026-11-04 — خارطة حيّة وليست نهائية

- **الدافع:** المستخدم يريد استخدام الخارطة مرجعًا للتطوير، مع مرونة إضافة/دمج/نقل/حذف مراحل حسب اكتشافات المحرك.
- **القرار:** اعتماد إجراءات التغيير في ROADMAP.md وDEVELOPMENT_PROTOCOL.md، مع تسجيل سبب وأثر أي تغيير جوهري هنا.
- **الأثر:** توثيق وإدارة مشروع فقط؛ لا تغيير في كود المحاكاة، ولا إعادة توصيف مراحل مكتملة.
- **الحالة:** معتمد تنظيميًا، وليس مرحلة برمجية.
- **المراجعة:** مع إغلاق كل مرحلة مؤثرة أو الوصول إلى معلم.

### G-002 — 2026-11-04 — تبكير حماية حفظ العالم

- **الدافع:** خطر بناء عالم طويل الأمد ثم فقد تاريخه بسبب تغيّر Schema/Rules أو نسخ SQLite غير متسق.
- **القرار:** إعداد SAVE_COMPATIBILITY_POLICY.md وإضافة بوابة **P0 قبل أول عالم دائم** حتى لو جاء قبل 01-Z، ومراجعة أمان/توافق في كل مرحلة؛ 05-C تبقى لتطوير منظومة النسخ والإدارة الأشمل.
- **الأثر:** شرط اعتماد جديد ومرجعية فحص؛ لم ننفذ backup/restore/migration برمجيًا ولم نغير Schema 12 / Rules 16.
- **الحالة:** مواصفات/سياسة فقط؛ P0 غير مغلقة.
- **المراجعة:** عند تغيير الإصدارات التالي وقبل أول تجربة طويلة الأمد.

> لا يجوز اعتبار «معتمدة تنظيميًا» مرادفًا لـ«مكتملة في الكود».

### G-003 — 2026-11-04 — تنفيذ بحث الغذاء 01-S وتبعات توافق الإصدارات

- **الدافع:** 01-R تجمع الطعام عَرَضًا بعد التحقيق ولا تجعل الجوع سببًا مقصودًا لبدء الفعل.
- **القرار:** `forage` نية مستقلة تستغرق 120 ثانية، تُسجل أسبابها محليًا وتُحسم وفق مخزون الموقع وقت الإنجاز؛ نجاح وفشل ثابتان في السجل.
- **البدائل:** عدم تغيير دلالة `investigate` القديمة؛ تأجيل ذاكرة المصادر البعيدة إلى 01-T.
- **الأثر:** Schema **12→13** وRules **16→17**؛ رفض القواعد القديمة دون هدم ملفاتها؛ P0 غير مكتملة.
- **الأدلة:** تجربة 7 NPC و51 حدثًا، 4 محاولات ونجاحان وفشلان؛ فحص سلوكي 472/472 على نسختي Python.
- **الحالة:** منفّذة ومختبرة؛ مراجعة مستقلة **معلّقة** قبل الإغلاق.
- **المراجعة التالية:** تدقيق 01-S ثم 01-T.

### G-004 — 2026-11-04 — تدقيق داخلي لتفاعل البحث والملاحة والمعرفة

- **الدليل:** فشل حالتين جديدتين في CI `41854606709`: شخصية جائعة تبدأ الملاحة وتغادر طعامًا مرئيًا في موضعها؛ وفشل حالة في `41855205489`: تتجاهل تحذير خطر وصلها.
- **القرار:** جعل نية البحث ذات الأولوية المحلية تسبق السفر الاختياري، وإدراج `danger` من **معتقدات الشخصية نفسها** بثقة >=80 كمانع للبحث المحلي. لا كشف لحقيقة عالمية ولا إجراء تلقائي لتغيير NPC آخر.
- **التبعات:** لا تغيير Schema 13 / Rules 17، ولا واجهة جديدة، ولا بيانات قصة؛ تُنقل سياسة خطر أشمل إلى 01-T/01-V عند الحاجة.
- **الاختبار:** [41855607762](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41855607762) = **481/481 ناجحًا على Python 3.10 و3.13**؛ تُوثق نتائج مراجعة المؤلف منفصلة عن الاعتماد المستقل.
- **الانتقال إلى OpenCode:** يستخدم [OPENCODE_HANDOFF.md](OPENCODE_HANDOFF.md) ويراجع أولًا دون بدء 01-T تلقائيًا.
- **الحالة:** إصلاحات مختبرة؛ بوابة التوقيع المستقل ما زالت مفتوحة.

### G-005 — 2026-11-04 — اعتماد مستقل لـ01-S وإغلاقها رسميًا

- **الدليل:** مراجعة مستقلة منفصلة عن المنفّذ على commit `785c349` شملت قراءة diff `01r..01s`، وتشغيل الاختبارات محليًا **481/481**، و**11 فحصًا عدائيًا مستقلًا** كُتب من قائمة المراجعة خارج المستودع (كلها ناجحة)، وإنشاء قاعدة 01-R حقيقية برفضها fail-closed دون تعديل صفوفها، وتعادل الأحداث والدلالات عبر الفرعين، وCI `41856382834` ناجحًا على 3.10 و3.13.
- **القرار:** الحكم **APPROVED** دون blockers؛ إغلاق 01-S وتحديث حالتها في ROADMAP.md إلى «مكتملة ومختبرة ومراجعة»، وفتح الباب أمام 01-T بتصميمه أولًا.
- **الملاحظات غير الحاسمة ومواضع معالجتها:** **OBS-1** سلامة الحفظ (`from_dict` للسجلات لا يتحقق من السلسلة التاريخية؛ الحماية من سجل الأحداث و`verify()`) → **بوابة P0 قبل أول عالم طويل الأمد + 05-D**؛ **OBS-2** مهلة القرار 60ث تقمع السفر الاختياري وتأخر بدء البحث → **اختبار انحدار في 01-U + مراعاة صريحة في تصميم 01-T**؛ **OBS-3** ترتيب منافسة أبجدي يfavor IDs ثابتة → **01-V**؛ **OBS-4** قرار forage يدوي معلّق ينفذ رغم إطفاء الـflag لاحقًا → ملاحظة توثيقية/تدقيق اختياري في **01-W**؛ **OBS-5** غياب اختبار صريح لـ«موقع القرار == موقع الإكمال» → اختبار اختياري في **01-U**.
- **الأثر:** توثيق فقط (phase_01s_report.md، ROADMAP.md، decisions.md، هذا السجل)؛ **لا تغيير في كود المحاكاة**، ولا Schema/Rules جديدان (تبقى 13/17)، ولا ترحيل، ولا تعديل لـmain أو ملفات القصة.
- **الحالة:** مُنفَّذ — دفع إلى `simulation-engine-phase-01s` فقط مع التحقق من CI على commit الإغلاق.
- **المراجعة التالية:** تصميم 01-T (معرفة مواقع الغذاء) للموافقة عليه قبل أي برمجة، ثم 01-U.

### G-006 — 2026-11-05 — الانتقال المشروط مع المراجعة الخارجية المؤجلة

- **المصدر والدافع:** موافقة المستخدم الصريحة على الاستمرار هنا لأنه لا يستطيع استخدام OpenCode حاليًا؛ لا يجوز تعطيل التطوير طويلًا بانتظار مراجع مستقل، ولا الادعاء بوجود توقيع غير صادر.
- **الدليل:** 01-T ناجحة تقنيًا على commit `14c672912a656cbb357647f63e6e2de91aef24e8`، GitHub Actions `41926367605`: 544/544 اختبارًا على Python 3.10 و3.13، وتقرير عدائي وتوافق نسخ؛ [طلب المراجعة #1](https://github.com/daboolgame123-creator/Carlos-RPG/pull/1) مفتوح بلا موافقة مستقلة.
- **البدائل:** (أ) وقف جميع المراحل حتى توفر OpenCode أو مراجع؛ (ب) اعتبار CI موافقة مستقلة؛ (ج) **المعتمد: انتقال مشروط مع تمييز حالة الاعتماد**. رفض (ب) لأنه يخلط الاختبار بالمراجعة.
- **القرار:** اعتماد الحالات `IN_PROGRESS` و`TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING` و`APPROVED / CLOSED` و`BLOCKED`. السماح ببدء 01-U على فرع مستقل فقط بعد نجاح آخر CI وتوثيق التبعيات؛ لا إغلاق رسمي لـ01-T إلا بمراجعة مستقلة.
- **الأثر:** تعديل تنظيمي في DEVELOPMENT_PROTOCOL.md وROADMAP.md وdecisions.md؛ لا تغيير في المحرك أو أرقام Schema/Rules أو قواعد replay، ولا رفع أو دمج إلى main. أي مشكلة لاحقة في 01-T تُراجع مع المراحل التابعة.
- **السلامة:** P0 لا تزال OPEN، ولا مجازفة بعالم محفوظ مهم أو ترحيل تلقائي، ولا تعديل لملفات القصة.
- **الحالة:** قرار موثق؛ 01-T تنتظر مراجعة خارجية؛ 01-U يبدأ بتصميم مستقل مشروط.
- **المراجعة التالية:** بعد اختبار 01-U أو عند توفر مراجع مستقل، أيهما أسبق.

### G-007 — 2026-11-05 — انتقال مشروط إلى تنقل الغذاء في 01-U

- **الدافع:** امتلاك الشخصية لمعلومة عن مصدر بعيد في 01-T دون تخطيط طريق إليه في 01-S.
- **البدائل:** قراءة المخزون البعيد أو خريطة عالمية (مرفوض)؛ اختيار أقصر طريق **تعلمته الشخصية** (معتمد).
- **القرار:** سياسة اختيار طريق غذاء جديدة بعلم افتراضي OFF، لا تتجاوز الجوع/التعب/الخطر/الأولوية المحلية؛ لا تتحول الشائعة إلى حقيقة أو غذاء.
- **الاختبار:** [41930579158](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41930579158) — 564/564 ناجحة على 3.10 و3.13 وتعادل أحداث وحالة 01-T.
- **الأثر:** تغيير سلوك opt-in فقط على 01-U، Schema 13 / Rules 18 ثابتة؛ لا main أو قصة أو ترحيل.
- **الحالة:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING؛ 01-T وP0 غير معتمدتين بعد.
- **المراجعة:** مراجعة مستقلة لـ01-U و01-T قبل الحكم بالإغلاق النهائي.

### G-008 — 2026-11-05 — أثر الندرة والرفض على قرار الشخصية (01-V)

- **الدافع:** الذاكرة والملاحة في 01-T/01-U تسمح بتخطيط سفر رغم فشل سابق أو العودة لنفس الرافض؛ المطلوب استجابة سببية للفشل.
- **البدائل:** حظر دائم (مرفوض)، كشف مخزون الآخرين (مرفوض)، أو إعادة اختيار مؤقتة من السجلات الخاصة بالشخصية (المعتمد).
- **القرار:** علم `scarcity_enabled=False` افتراضيًا؛ يستند فقط إلى سجل فشل جمع الغذاء الخاص بالشخصية وطلبات مساعدتها المرفوضة. فترتا تردد مستقلتان، كل واحدة 3600 ثانية من الزمن المنطقي؛ مهلة إعادة طلب المساعدة الأصلية 900 ثانية محفوظة.
- **الدليل:** [CI 41989436509](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41989436509): **587/587** على 3.10 و3.13؛ تحويل فعلي محدود بين طرفين بعد رفض الأول، مع replay وsnapshot ورفض تكرار الأمر والميزانية الذرية؛ تطابق 01-U فعليًا عند تعطيل العلم الجديد.
- **الأثر:** سلوك تخطيط opt-in فقط على فرع 01-V؛ Schema 13 / Rules 18، بلا أحداث جديدة ولا ترحيل أو تعديل على main/قصة كارلوس.
- **الحالة:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING؛ 01-T و01-U ما زالتا معلقتين، وبوابة P0 مفتوحة.
- **المراجعة:** انتظار نتيجة مراجع خارجي مستقل للمرحلة ولتبعياتها قبل إغلاقها رسميًا.

### G-009 — 2026-11-05 — تسلسل إصلاح المراجعة وتأجيل الاعتماد الخارجي

- **الدافع:** حجب OpenCode مرحلتي 01-T/01-U بسبب انفجار أخبار 25 شخصية وتعطل معالجة معرّف طويل وتجاوز مهلة الاستكشاف. المستخدم قرر إكمال التطوير هنا وتأجيل المراجعة الخارجية.
- **القرار:** فروع إصلاح متفرعة مع آباء Git صريحين تحفظ التاريخ، وتصحيح تخطيط تبادل الغذاء والتحصين وقرار الاستكشاف، وتوريثه إلى 01-V.
- **الدليل:** 01-T = 548، 01-U = 569، 01-V = **593** اختبارًا ناجحًا على كلا إصدارَي Python. [CI 01-V 42013057857](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42013057857) يشمل 25 شخصية وكل مزايا الغذاء والملاحة والمساعدة والندرة، وتكافؤ السجل والحالة مع الأسلاف المصححة.
- **الأثر:** Schema 13 / Rules 18، لا هجرة ولا تعديل على main أو ملفات القصة، ولا إغلاق لبوابة P0.
- **الحالة:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED للمراحل المصححة، وليس اعتمادًا مستقلًا؛ الأحكام BLOCKED على الإصدارات التاريخية محفوظة.

### G-010 — 2026-11-05 — بوابة أوامر اللاعب والانتقال إلى Rules 19

- **الدافع:** معلم M2 يتطلب أن يختار اللاعب أفعال كارلوس بدل تخطيطها NPC آليًا؛ نظام السفر القديم مخصص لـNPC.
- **البدائل:** تقديم كارلوس كـNPC مموّه (مرفوض: يضيع استقلال قرار اللاعب)؛ انتقال فوري أو تعديل مباشر لقاعدة البيانات (مرفوض: غير سببي)؛ **إشارة سفر لاعب موثقة تنفذ عند موعدها** (معتمد).
- **القرار:** PlayerGateway موثوقة داخل برنامج محلي فقط، تدعم inspect/move/wait/interact؛ حدث player travel مجدول، ويُرفض السفر المكرر والتلاعب وإلغاء الرحلة. نتائج محدودة محليًا دون إفشاء عالم كامل.
- **توافق:** Schema 13 / Rules 19 عن قصد؛ رفض قراءة عوالم 13/18 الأصلية بأمان، ولا ترحيل. [CI 42021241326](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42021241326) تثبت 607 اختبارًا ناجحًا على كل Python، وتطابق أحداث وسلوك الأسلاف عند استثناء رقم Rules فقط.
- **التبعيات:** 01-X لاكتمال الرؤية والمعرفة المقيدة؛ P0 ما زالت OPEN قبل أي عالم طويل الأمد، وAuthN/AuthZ قبل أي وصول شبكي.
- **الحالة:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED، المراجعة المستقلة مؤجلة؛ لا تعديل على main أو القصة الأصلية.

### G-011 — 2026-11-05 — اختبار 01-Z دون تجاوز شرط حفظ P0

- **الدافع:** 01-Z يهدف إلى استئناف عالم صغير، لكن لا توجد قبلها أداة نسخ احتياطي مستقلة مجرّبة ولا مراجعة استعادة إنتاجية. المستخدم طلب متابعة التطوير دون انتظار المراجعة الخارجية.
- **البدائل:** (أ) السماح بحفظ دائم بلا نسخة (مرفوض)، (ب) إيقاف التطوير كليًا (غير مطلوب)، (ج) بناء مرشح P0 مع حلقة `disposable-test` فقط مع حجب الاعتماد الدائم (**المعتمد**).
- **التغيير:** أدوات نسخ SQLite متسق وحزمة manifest ومطابقة كامل إعادة التشغيل واستعادة إلى ملف منفصل، وجلسة قابلة للفتح بعد انقطاع العملية مع الوقت متوقفًا، وCLI تجريبي يحفظ checkpoints منفصلة. لا استيراد من القصة.
- **الأثر:** لا تغير Schema 14 / Rules 21 ولا أحداث المحاكاة أو سلوك NPC. فحص 7 شخصيات والتوافق والمراحل السابقة يستمر، والحفظ الدائم لا يزال محظورًا.
- **الدليل التقني:** [CI 42059385146](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42059385146) — 643 اختبارًا ناجحًا على Python 3.10 و3.13 مع تشغيلين مستقلين واستعادة منفصلة.
- **المخاطر المتبقية:** نجاح CI لا يثبت سلامة انقطاع الطاقة، race لإنشاء مجلد backup نفسه، الصلاحيات وأنظمة الملفات، سرعة الاستعادة أو النسخ الخارجية. [طلب مراجعة مستقلة](phase_01z_p0_independent_review_request.md).
- **الحكم:** 01-Z **TECHNICALLY_TESTED فقط في disposable-test**؛ بوابة P0 **OPEN** والمراجعة الخارجية **DEFERRED**، ولا يعد هذا APPROVED/CLOSED.

### G-012 — 2026-11-05 — تجدد بيئي محدود دون اختراع غذاء (02-A)

- **الدافع:** غذاء المواقع كان ينفد بصورة صحيحة في M1، لكن لم توجد سياسة موثقة لإعادة تزويده دون خلق موارد مجانية. معلم M3 يحتاج مخزونات بيئية متغيرة وسببية.
- **البدائل:** تجدد دائم تلقائي من لا شيء (مرفوض)؛ حسابات زراعة/طقس بلا بيانات أصلية (مؤجلة)؛ **تحويل محدود من احتياطي موقع معروف وبزمن ومقدار محددين** (المعتمد لهذه المرحلة).
- **القرار:** إعداد موقع مؤقت `EnvironmentalCycleConfigured` عند التهيئة: `regrowth_reserve` معروف ومحدود، و`wild_food` معروف، وسعة نهائية، وفترة منطقيّة. في كل استحقاق يُحوّل بحد أقصى 1 إلى 1، لا يستهلك شيئًا عند امتلاء المخزون ولا يخلق احتياطيًا. وعند نفاد الاحتياطي تُوقف الجدولة حتى لا تنتج أحداثًا فارغة بلا نهاية. لا معرفة بعيدة للشخصيات.
- **الدليل:** [CI 42063848371](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42063848371): 657 اختبارًا لكل Python 3.10 و3.13 (14 اختبارًا جديدًا). فحص 7 NPC ومصادر محدودة وتكافؤ replay وsnapshot ورفض الأحداث المزورة والتكرار والتنازع وتوافق الأسلاف. [طلب مراجعة مستقلة](phase_02a_independent_review_request.md).
- **أثر التوافق:** Schema 15 / Rules 22 نتيجة الحقل والحدث والدلالة الجديدة؛ ملفات 14/21 لا تُقرأ ولا تُحوّل صامتًا.
- **الحالة:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED؛ **P0 OPEN**، ولا تعديل على main أو قصة كارلوس؛ التجارب disposable فقط.

### G-013 — 2026-11-05 — إنتاج مصدري محدود بوصفات ومهنة ووقت (02-B)

- **الدافع:** المرحلة 02-A أمنت موارد بيئية محدودة، لكن NPC لم يمتلك عملية إنتاج تصنع سلعة بعد عمل حقيقي ومدخلات فعلية؛ لا يكفي عدّ وحدات العمل الوهمية إنتاجًا اقتصاديًا.
- **البدائل:** توليد المنتج فور اختيار مهنة (مرفوض)، تحويل محرك العمل القديم إلى إنتاج سلعي شامل بلا قواعد (مرفوض)، **مسار إنتاج محلي اختياري وصريح** به وصفة ومهنة وأدوات ومدخلات ومؤقت (المعتمد).
- **العقد:** `ProductionRecipeConfigured` موثوق عند التهيئة؛ `ProductionStarted` يحجز حبوب الموقع فورًا عبر صلاحية `production_authorized` موثقة؛ موعد `ScheduledEventFired` فقط يُنتج الخبز ويثبت المدخل والمخرج. لا يمكن إلغاء عمل محجوز حتى تُصمَّم سياسة رد المواد والتعويض.
- **الندرة:** تتحقق المهنية والموقع، ولا يسمح للعامل بالسفر أو بدء عمل ثانٍ؛ العدد المتزامن لا يتجاوز عدد الأفران الحقيقي في الموقع؛ لا منتجات بلا مدخلات معلومة، ولا أجور أو أدوات مستهلكة من دون قاعدة.
- **الدليل:** [CI 42068908977](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42068908977): **673 اختبارًا ناجحًا لكل Python 3.10 و3.13**، وفيه 16 اختبارًا جديدًا، و7 شخصيات، وإعادة فتح وحفظ وفحص رفض عالم 15/22 القديم. [طلب المراجعة المستقلة](phase_02b_independent_review_request.md).
- **تغيير التوافق:** Schema 16 / Rules 23 مع مجموعتي `production_recipes` و`production_jobs` وعمود صلاحية جديد في سجل الأوامر؛ لا ترحيل من 15/22 ولا وصول غير موثوق.
- **الحالة:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED — ليست APPROVED/CLOSED؛ P0 OPEN و`main` وملفات الرواية غير معدَّلة؛ العوالم disposable فقط.

### G-014 — 2026-11-05 — ملكية وسوق محلي بعرض سعر معلوم دون اختراع نقود (02-C)

- **المشكلة:** 02-B ينتج الخبز في مخزون موقع المخبز، ولم يكن هناك سبب صحيح لنقله إلى مخزون شخصية أو قبض ثمنه. نقل الملكية بلا صاحب أو اقتطاع العملات من الهواء يخالف مصدر الحقيقة.
- **القرار:** إسناد `keeper_id` لمخزون موقع محدد عند التهيئة الموثوقة؛ أمين السوق يعرض سلع المخبز **نيابة عن الموقع**، فيذهب الثمن إلى رصيد الموقع نفسه، لا إلى جيبه. ويمكن لـNPC عرض ملكيته الشخصية فقط. `MarketOfferPosted` يوثّق السعر ووحدة المقابل، `MarketTradeExecuted` ينقل السلع والنقود/المقايضة كحدث واحد ذري مع 8 أرصدة قبل وبعد ووقت ومصدر، و`MarketOfferClosed` يوقف عرضًا غير محجوز. لا تخمين لبيانات ناقصة.
- **الحدود:** الأسعار **عروض محلية من البائعين** قابلة للفحص والتفسير، وليست توازن طلب/عرض تلقائيًا أو تكوين سعر ديناميكي. لا مديونية أو تسليم عن بعد أو أحكام ملكية قانونية أو اقتصاد NPC مستقل حتى الآن.
- **الدليل:** [CI 42074833117](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42074833117) — 697 اختبارًا ناجحًا لكل Python 3.10 و3.13 (24 جديدًا). سيناريو 7 شخصيات يربط إنتاج 2 رغيف وبيعها بـ6 نحاس، ويجتاز replay والاستعادة ورفض 16/23 الأصلي. [طلب المراجعة المستقلة](phase_02c_independent_review_request.md).
- **التوافق:** Schema 17 / Rules 24 ومجموعات `market_stalls/market_offers/market_trades` وعمود `market_authorized` بسجل الأوامر؛ رفض نسخ 16/23 القديمة بلا تعديل/ترحيل.
- **الحكم:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED، P0 OPEN. هذا عالم disposable-test لا أصل قصة كارلوس؛ `main` غير معدل.

### G-015 — 2026-11-05 — قروض 02-D ممولة وموثقة
- **الدافع:** عرض القرض ليس دينًا ولا عملة، والديون لا تختفي بالسفر أو بالإنفاق.
- **القرار:** `LoanProposed` عرض؛ `LoanAccepted` انتقال فعلي لقطع النحاس بموافقة المقترض؛ `LoanRepaid` سداد موثق جزئيًا أو كاملًا. وقت الاستحقاق يوسم الدين `overdue` بلا مصادرة أو غرامة، ويظل `defaulted_at` محفوظًا بعد السداد.
- **الاختبارات:** [CI 42079223232](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42079223232): 724/724 لكل Python 3.10 و3.13، 27 جديدة، 7 شخصيات تتعامل مع السوق والسفر والدين، فحص backup/replay ورفض ملفات 17/24 القديمة.
- **التوافق:** Schema 18 / Rules 25، `loan_contracts` و`loan_repayments` و`loan_authorized`. لا تحويل تلقائي ولا تغيير على `main`.
- **الحالة:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED؛ P0 OPEN والعالم تجريبي.


### G-016 — 2026-11-05 — إلزام توثيق الوظائف الجوهرية المكتشفة وعدم ضياع النواقص

- **المصدر:** طلب المستخدم أن كل مهمة مهمة لنظام عالم كارلوس تُثبت بوضوح في المشروع فور اكتشافها، حتى إذا أُجّل التنفيذ.
- **الدافع:** كشفت 02-F ثلاث فجوات مهمة لم تعد عبارة «لاحقًا» كافية لتتبعها: مقاطعة العمل/السفر عند الطوارئ، الأجور وعقود العمل، وحق السكن والملكية.
- **البدائل:** (أ) تجاهلها حتى يحين التنفيذ (مرفوض لاحتمال النسيان)؛ (ب) إدخالها فورًا كلها في 02-F (مرفوض لتضخم النطاق ومخاطر الأمان)؛ (ج) **سجل متطلبات صريح ومراجعته قبل المراحل الجديدة** (معتمد).
- **القرار:** إضافة قاعدة إلزامية إلى ROADMAP.md §14: معرّف ثابت، أهمية، مرحلة تنفيذ مرشحة أو عدم تحديدها صراحة، التبعيات، المخاطر، اختبارات القبول، وروابط متبادلة مع التقارير. لا يُسمّى تسجيل الفكرة تنفيذًا. لا تُلغى أو تُعدّل مرحلة بلا سجل سبب.
- **القيود الجديدة:** WORLD-GAP-001 (إلغاء/مقاطعة آمنة، مرشح 02-F2 قبل المخاطر المعقدة)، WORLD-GAP-002 (أجور وتوظيف، مرحلة اقتصادية غير مرقمة)، WORLD-GAP-003 (سكن وحقوق ملكية/إيجار، مرحلة غير مرقمة). تصنيفات وتبعيات تفصيلية في ROADMAP.md.
- **أثر التبعيات:** يمكن متابعة 02-G ضمن النطاق السابق إذا لم يعتمد على هذه المهام؛ يجب إعادة فحص القيود قبل 03-A–03-D و04-A وأي معلم اقتصادي أو تشغيل عالم طويل الأمد.
- **Schema/Rules:** لا تغيير؛ يبقيان 20/27. التغيير وثائقي فقط ولا يسمح بترحيل عالم قديم أو تشغيل إنتاجي.
- **الحالة:** القاعدة معتمدة تنظيميًا؛ المتطلبات الثلاث **مسجلة ولم تُنفذ**. المراجعة المستقلة لـ02-F مؤجلة وP0 مفتوحة.
- **المراجعة التالية:** عند تخطيط 02-G، وعند كل مرحلة/معلم يتأثر بهذه التبعيات.


### G-017 — 2026-11-05 — 02-G شائعات مسندة بدل خلق حقائق من الكلام

- **المصدر والدافع:** تجربة كارلوس تستلزم انتشار قول مثل «أيها العفريت» عبر أشخاص حقيقيين دون تحويل خباز بشري إلى عفريت؛ والسمعة شخصية لا قرار عقوبة عالمي. راجع [تصميم 02-G](phase_02g_design.md) و[تقريرها](phase_02g_report.md).
- **البدائل:** (أ) نموذج لغوي يضيف حقائق مباشرة (مرفوض)؛ (ب) شائعات فورية تشمل الجميع (مرفوض)؛ (ج) سجل مصدر حقيقي ورحلة معلومة محدودة عبر NPC متجاورين (المعتمد كأول شريحة).
- **القرار:** `RumorDelivered` عن `SocialMessageReceived` حقيقية، سلسلة الأبناء، تأخر تناقل، حد للمسافة وعدد القفزات والثقة، و`perceived_reputation` موقف غير محسوم لا إدانة. لا يتم تفسير اللغة الحرة الآن، ولا رفض تجاري آلي.
- **التوافق:** Schema 21 / Rules 28 بسبب مجموعة `rumor_deliveries` الجديدة. أي عالم 20/27 سابق يُرفض بلا تغيير أو ترحيل ضمن اختبارات CI.
- **التبعيات والنواقص الملزمة:** WORLD-GAP-001..003 تبقى مفتوحة؛ تسجيل WORLD-GAP-004 (تفسير الكلام والمزاح/الإهانة بمصدر) وWORLD-GAP-005 (تأثير السمعة المحلية في قرار التجارة). لا تساوي الخطط تنفيذًا.
- **حالة التنفيذ:** تنفيذ أول شريحة واختبارات على فرع `simulation-engine-phase-02g`؛ لا يعتبر APPROVED أو TECHNICALLY_VALIDATED إلا بدليل CI أخضر على SHA نهائي، والمراجعة المستقلة ما زالت مؤجلة وP0 OPEN.
- **المراجعة التالية:** بعد اختبار 02-G وقبل اختيار امتداد السمعة أو الانتقال إلى 02-H.


### G-018 — 2026-11-05 — إثبات تحقق 02-G التقني دون إغلاق المراجعة

- **الدليل:** [GitHub Actions 42102597539](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42102597539) على Commit الكود `7b7deaa8f4ef17f77600332aec1a588e8d16478d`: **763/763 اختبارًا ناجحًا** على Python 3.10 و3.13، تشمل اختبار قرية سبع شخصيات مع تناقل إشاعة ثلاث مرات، فحص إرجاع العالم، وتكافؤ المراحل السابقة عندما تكون الشائعات معطلة ورفض عالم 02-F الحقيقي بلا تغيير.
- **الحكم:** `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED`؛ لا إعلان `APPROVED/CLOSED` دون مراجع مستقل، ولا تجاوز شرط الحفظ الإنتاجي P0.
- **التبعيات:** WORLD-GAP-001..005 ما زالت مسجلة؛ لا تعد هذه المرحلة قادرة على فهم المزاح والنبرة اللغوية أو فرض قرارات تجارية من الشائعات قبل تصميم وتحقق لاحقين.
- **التوافق:** Schema 21 / Rules 28؛ لا ترحيل تلقائي أو تشغيل عالم طويل الأمد، ولا تعديل `main` أو ملف القصة الأصلي.
- **المراجعة التالية:** [طلب المراجعة المستقلة لـ02-G](phase_02g_independent_review_request.md) ثم تصميم 02-H وفق ترتيب الخارطة مع فحص المتطلبات الجوهرية المفتوحة.

### G-019 — 2026-11-05 — Phase 02-H1: physical taking, distinct from accusations

- **Reason:** 02-C tracks owned inventory but did not permit materially recorded non-consensual possession changes. An allegation or rumor must never create a theft or a punishment.
- **Decision:** introduce independently authorized and event-sourced `PropertyTaken` with actual physically present NPC, verified finite site or person-owned resource balance, exclusive atomic transfer, source/target ledger and no automatic discovery. Registered steward separates site stock from a character's personal property. Recipe-bound production equipment remains protected until reservation-aware handling exists.
- **Proof:** code `ec5d7eb0633a24554636c77cb3b0efde18f7a8a7`; [CI 42105931046](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42105931046) **773/773 passing each on Python 3.10 and 3.13**; actual 02-G Schema21/Rules28 saved-world refusal without file mutation, replay, seven-NPC resource conservation, market non-double-sale, authorization and failure atomicity.
- **Compatibility:** Schema **22**, Rules **29**, `property_takings` collection, `taking_authorized` command provenance. No implicit migration; legacy off-parity ignores only the newly empty ledger.
- **Deferred:** 02-H2 witnesses/claims; 02-H3 complaint intake; institutional penalties/restitution/real-estate titles are not supplied by H1. WORLD-GAP-001..005, external independent review, and P0 remain OPEN. No `main` or story-file changes. [H1 report](phase_02h1_report.md).

### G-020 — 2026-11-05 — Phase 02-H2: real-time witnesses versus unproven claims

- **Problem:** physically recorded taking in 02-H1 did not distinguish what actually happened from what any specific character witnessed or merely alleged; a global event log must not become universal NPC knowledge.
- **Decision:** optional contemporaneous witness IDs on atomic `PropertyTaken` only; verified physical locality but NOT guaranteed automatic perception. Store per-witness provenance and independent `PropertyClaimFiled` ledger for unverified allegations, losses and title assertions. A taking reference may be cited only by the taking actor or a recorded witness. No guilt, prosecution, restitution, possession changes, or global NPC knowledge are inferred.
- **Proof:** [CI 42108021281](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42108021281) at `ff2d9b87f91004a1155397debe8fc74b8cc38c52`, **787/787** per Python 3.10 and 3.13, including a 7-person disposable village and actual H1 saved-world fail-closed verification.
- **Compatibility:** Schema **23** / Rules **30**, sighting/claim ledgers and distinct `claim_authorized` command provenance; H1 worlds are deliberately rejected unchanged, no silent migration; historical semantic comparisons strip only new empty ledgers.
- **New documented gaps:** WORLD-GAP-006 actual attention/visibility/stealth detection before deeper hazards; WORLD-GAP-007 legal title versus physical possession before any return or judicial enforcement. Existing WORLD-GAP-001..005 remain OPEN.
- **Status:** H2 `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED`, NOT independently APPROVED/CLOSED; 02-H3 complaint intake pending; P0 OPEN; original Carlos narrative and `main` untouched. [H2 report](phase_02h2_report.md).

### G-021 — 2026-11-05 — Phase 02-H3: real complaint intake, no guilt or punishment

- **Purpose:** allow a local official to receive a specific already-filed property claim, without implicitly deciding guilt or fabricating legal authority. A character can lie and still lodge a complaint; an officer's acknowledgment says only that it was received.
- **Decision:** explicit time-zero bootstrap desk assignment and one designated officer per physical site; trusted active-session `PropertyComplaintReceived` and `PropertyComplaintAcknowledged` events; enforce claimant identity/presence and officer presence/authorization; claimant may leave after intake; duplicate and forged attempts rejected. Never alter balances, sanctions, title, NPC knowledge or original `unverified` status.
- **Proof:** `f102274c584f26f82d3d54e7eb42d7cad628715a`, [CI 42109843738](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42109843738), **802/802 tests green on each Python 3.10 and 3.13**; seven-NPC complaint and traveling-officer adversarial tests, replay and prior-world rejection.
- **Compatibility:** Schema **24**, Rules **31**, `complaint_desks` + `property_complaints` ledgers, independent `complaint_authorized` persisted command provenance; genuine H2 Schema23/Rules30 save refused unchanged; semantic parity ignores only new, feature-off empty ledgers.
- **Deferred & documented:** WORLD-GAP-008 rotating duty, delegation, abandoned/closed desk intake, referral/jurisdiction; WORLD-GAP-006/007 witness perception and property title; independent legal adjudication/sanctions under institutional follow-on; previous gaps 001..005 unchanged. This is **not** a courthouse or authenticating user-facing API.
- **Gate:** H1/H2/H3 implementation `TECHNICALLY_VALIDATED` but independent review **DEFERRED**, production backup/recovery **P0 OPEN**; no `main` merge or story changes. [02-H3 report](phase_02h3_report.md).
