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

### G-022 — 2026-11-05 — Internal adversarial review: prevent contradiction laundering through eyewitness IDs

- **Found:** REVIEW-02H-001. An actual witness to `PropertyTaken(t1, basim, bread, 1)` could file an accusation against `adel` claiming the same `t1` as `direct_sighting`, or exaggerate the quantity to `100`. Prior H2 provenance verified that the witness saw **a** real taking, not that the claimed actor and amount matched. The status remained `unverified`, but the cited evidence was misleading to any future adjudicator.
- **Repair:** require cited taking quantity and (for `accusation`) actor to equal the immutable taking; duplicate this check in persisted snapshot validation. False allegations remain legal as `taking_id=None, basis=unverified_statement`, never certified by contradictory evidence.
- **Evidence:** six new adversarial probes in `test_property_02h2.py`, including rehashed event forgery, mismatched snapshot, stripped capability, and preservation of unverified standalone lies. Code checkpoint `65e4dd582d8ea0a4cfbd442a8ce39e094aa5f303`; [CI 42112812532](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42112812532) **SUCCESS — 808/808 on each Python 3.10 and 3.13** on exact code SHA 65e4dd582d8ea0a4cfbd442a8ce39e094aa5f303.
- **Compatibility:** Schema stays **24**, Rules **31 → 32**, strict rejection of an authentic pre-review 24/31 saved world without changing any bytes. No implicit migration or `main` modifications.
- **Separate unresolved findings:** identity/authentication at API boundary; trusted witness-selection is not real perception; title vs custody and office staffing; independent P0 recovery certification. See [internal adversarial audit](phase_02h_internal_adversarial_audit.md). This is not separate independent approval; external review and P0 remain OPEN.

### G-023 — 2026-11-06 — Study first: legal rights, jurisdiction, evidence and nonmagical adjudication

- **Trigger:** the user explicitly requested a real study before any judicial system implementation; building courts/sanctions straight from 02-H complaint acknowledgment would incorrectly equate physical custody with legal ownership and allegations with guilt.
- **Evidence reviewed:** current 02-H Rules32 code and exact green CI 42112812532 (808/808 Python 3.10/3.13), 02-H design and internal adversarial audit, current development protocol, roadmap, persistence and property/complaint modules. External comparative sources: English manorial courts (UK National Archives), ICCPR Article 14 (UN), civil/criminal burdens of proof (Cornell LII), NIST 800-53 separation of duties and audit provenance.
- **Study deliverable:** [LEGAL_AND_JUSTICE_FEASIBILITY_STUDY.md](LEGAL_AND_JUSTICE_FEASIBILITY_STUDY.md). Analyzes six separate layers (physical truth, legal entitlement, actor knowledge, presented evidence, judgment, enforcement); compares alternative designs; registers GATE-LAW-01..07; recommends optional civil-case-only stages 04-A/J0..J5 and a later separate criminal system; includes 16 seven-NPC adversarial scenarios.
- **Roadmap:** updates stale "current execution" preface to observed 02-H Rules32; keeps 04-A **PLANNED** with only a study; adds WORLD-GAP-009 for legal title/law/jurisdiction/evidence prerequisites while retaining WORLD-GAP-001..008, P0 and independent review.
- **Status and boundary:** **RESEARCH / DESIGN ONLY — NOT APPROVED FOR IMPLEMENTATION**. No engine source, event, schema, rules, original story, or main changes. No assumed law of Carlos's world or fictional court hierarchy; these decisions require future explicit design adoption.

### G-024 — 2026-11-06 — Begin 04-A/J1a: historical origin-of-entitlement evidence only

- **Approval:** the user authorized starting after the feasibility study. Forked verified 02-H head `5b37787dadd226279ed81513efd59ffcca7ade4c` into **simulation-engine-phase-04a-j1**. Did NOT modify main, the actual Carlos story files or a long-lived test world.
- **Design choice:** fungible bread cannot be treated as an individually identified physical object, and warehouse balances are not current legal title. Implement *only* trusted time-zero original entitlement registration of a quantity at a physically known source with site steward / original personal holder, persisted as immutable `historical_origin_only`. Selling or physically taking bread leaves the historical origin record unchanged. It is NOT current ownership, lawful permission, a court order or execution.
- **Code:** `rights.py`, `PropertyTitleOriginRegistered` reducer, `WorldState.property_title_origins`; additional authenticated bootstrap provenance. No new capabilities to untrusted clients; no stock transferred by registering a right.
- **Guards:** bounded registered quantity cannot exceed recorded initial source balance, overlapping registrations are checked both on event append and detached snapshot consistency, forbids copper/counters/unknown owners, duplicate ID, untrusted events and malformed records.
- **Version:** Schema **24 → 25**, Rules **32 → 33**. Genuine 02-H Schema24/Rules32 old-world refusal without modification tested via CI workflow; no automatic migration.
- **Tests:** new seven-NPC adversarial suite `test_rights_04a_j1a.py`, legacy feature-off parity, snapshot/replay/rollback and old-version rejection. **Verified:** [CI 42117075269](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42117075269), exact code `ca79973bce536b1853b8d5a8b9d0efc049154aad`, **826/826 tests SUCCESS each on Python 3.10 and 3.13**. Status J1a TECHNICALLY_VALIDATED; independent review and P0 OPEN.
- **Scope left OPEN:** J1b lot allocation and provenance on all goods transfers, J1c ownership/title grants and transfers, independent review, P0 production recovery, laws/jurisdiction/court J2–J5. [Design](phase_04a_j1_design.md) / [Report](phase_04a_j1a_report.md). **J1a TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN**.

### G-025 — 2026-11-06 — J1b: conservative fungible-stock custody, not current legal title

- **Problem:** a historical J1a original-entitlement certificate does not follow a physical loaf through taking, sale, gift, consumption or mixing. Merely assigning an origin by stock count fabricates provenance.
- **Decision:** newly registered J1a origins seed separate physical custody lots. Their registered quantity is conserved as `known_holders + unresolved_quantity + exited_quantity`. Reconcile **all event-caused physical stock changes** using the pre/post resource maps. Only unambiguous transfers propagate certified holdings; ambiguous partial removal from a mixed/partly unregistered inventory downgrades all affected known provenance to `unresolved`, never guesses a specific loaf. Physical consumption/production inputs retire units only when their origin is determined. Both merchandise and barter payment goods are traced. No title, consent, lawful acquisition, court or punishment inferred.
- **Code:** new `simulation/src/carlos_sim/custody.py`, links from `rights.py` and `domain.py`, durable `property_custody_lots` and `property_custody_moves`. State and replay version changes from **Schema25/Rules33 → Schema26/Rules34**. Feature-off previous results match frozen semantic digests ignoring only new empty collections. Genuine J1a old database rejected byte-identically, without migration.
- **Tests/evidence:** [CI 42121040731](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42121040731), **841/841 tests on each Python 3.10 and 3.13**, exact code `82332a7c5f958a113d09d2924ae4fd6bedddcb7a`. 7-NPC bread-taking/resale, ambiguous partial mixes, full multi-origin transfer, assistance, consumption, production input, independent barter payment leg, forged snapshot, source conservation and complete replay/rollback.
- **Deferred:** J1c legally effective rights and grants, physical lot sorting/disambiguation (WORLD-GAP-010), adjudication and restitution, independent review, and P0 production backup/recovery. All remain **OPEN**; this is **TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN**, not approval or legal ownership.
- **Docs:** [J1b design](phase_04a_j1b_design.md), [J1b report](phase_04a_j1b_report.md). Main/story untouched.

### G-026 — 2026-11-06 — J1c1: explicit local collection permission, not transferable legal title

- **Reason:** source possession plus `PropertyTaken` and historical J1a origins cannot by themselves prove legal title or consent; legitimate explicit collection permission must be recorded as an independent, limited, traceable act rather than inferred from market trade or a historical source.
- **Implemented:** `PropertyPermissionGranted` and `PropertyPermissionRevoked` via separate active-session `permission_authorized` capability persisted in the immutable command log and replay. Only recorded origin beneficiary/registered steward may grant a named local NPC the `collect` scope for a fixed, exclusively traceable origin/source/commodity/quantity, with logical expiry and cap of seven days. Sum of currently reserved grants cannot exceed certifiable stock. Revocation requires grantor+grantee in person; not remote telepathy.
- **Redemption:** physical `PropertyTaken` can optionally cite `permission_id`; checks actor, grant status, time, matching resource/source/site and sufficient unmixed physical goods before debiting the actual inventory. Used quantity and exhaustion are permanent, verified against linked taking records. Without a cited grant H1 physical taking remains possible as `no_grant_recorded`, **not a theft verdict**.
- **Same-tick semantics:** a valid earlier use followed by revocation during the same logical second remains valid; the event/revision order, not only timestamp equality, determines historical permissibility on replay. Any subsequent use after revocation is refused.
- **Compatibility:** **Schema26/Rules34 → Schema27/Rules35**, new `property_permissions` collection, expanded taking provenance, one additional separately stored and replay-validated capability; a genuinely persisted Schema26/Rules34 J1b world is refused without altering its bytes. Feature-off parity omits only empty new collection; no migration or changes to `main` or original Carlos story.
- **Evidence:** [CI 42127560935](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42127560935) **865/865 SUCCESS each** Python 3.10 and 3.13 at exact code `9d573b0472ecf721afa8f4672d02312af22e86ce`. Tests include real grant-backed taking, quotas, mixed origins, impersonation, remote/expired/revoked grants, stock depletion, same-tick revocation, detached forged snapshot and replay.
- **Not implemented:** **J1c2/J1c3** recorded entitlement transfers, sale/use/hold grants and nonlocal notice; legal code, court, law enforcement, restitution, title transfer, and legal judgment. Independent review and production recovery **P0 OPEN**. [Design](phase_04a_j1c_design.md) / [J1c1 report](phase_04a_j1c1_report.md).

### G-027 — 2026-11-06 — J1c2a: explicit voluntary assignment of a historical claim, NOT automatic legal title

- **Problem:** physical exchange and J1c1 collection permission must not transfer a prior owner's historical recorded rights automatically, especially after a theft or unwitting resale.
- **Decision and scope:** add a separately conserved quantitative `registered_claim_balances` ledger seeded by each J1a historical origin. A proposed transfer (`RegisteredClaimTransferOffered`) reserves at most the account's available historic units but has no legal or physical effect by itself. A named recipient's **in-person** `RegisteredClaimTransferAccepted` records dual consent and atomically moves *registered claim units* plus a durable receipt. The proposer may cancel in person; an expired proposal cannot be accepted, and ceases to reserve. Parties may agree to a second reassignment, but no possession, sell permission, police power, legal title, restitution or court judgment is inferred.
- **Security:** an independently stored, replayed `claim_transfer_authorized` event capability and active session are required; fake identity, absent party, traveling recipient, invalid amount, duplicate, reserved overbooking, expired proposal and stale revision fail closed. Detached snapshot validation compares balances with actual accepted receipts, while full event replay proves chronology.
- **Version:** Schema **27→28**, Rules **35→36**; authentic prior Schema27/Rules35 world is refused with identical bytes, no silent migration or import of Carlos story; feature-off semantic parity still preserves original behavior.
- **Evidence:** [CI 42131594796](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42131594796) **889/889 tests passed EACH** Python 3.10 and Python 3.13, code commit `ac0eed8b0e34036cae14c302f2b6dcadb8df6b62`. Seven-person trading, transfer offer/accept/cancel/expiry, theft and market not moving claims, resale of claim, remote rejection, rollback, forged snapshots and replay.
- **Unclosed gates:** J1c2b legal title and third-party rights, J1c3 extended permission scopes, independent review, P0 backup and production recovery, law/jurisdiction and J2–J5 court systems. Report: [J1c2a](phase_04a_j1c2_report.md). Design: [J1c2](phase_04a_j1c2_design.md). **TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN**, not approved.


### G-2026-11-06-J1C2 — Technical closure and new external-validation policy
- Owner explicitly deferred separate external independent review and instructed direct execution of all feasible tests, with a ledger of requirements needing OpenCode/real-device/production verification. This supersedes the prior independent-review-as-universal-development-stop rule, **without** marking external review as passed.
- J1c2a engineering closed for disposable trusted-world development based on **905/905 full tests** in each Python 3.10/3.13 and successful additional adversarial/backup jobs in Actions 42199572310/42199572367. A separate, non-pytest 7-actor, 37-event SQLite backup/restore experiment passed both versions in Actions 42201414528.
- Production P0 and untrusted-access AuthN/AuthZ remain unapproved/blocked, tracked in [EXTERNAL_VALIDATION_LEDGER.md](EXTERNAL_VALIDATION_LEDGER.md). Existing real bugs must still be fixed; deferral only changes review scheduling.
- J1c2b opened for **analysis/design only** with explicit law/jurisdiction/lot-provenance dependencies. [Design and source audit](phase_04a_j1c2b_design.md). No code/version migration, `main` or narrative change.

### G-2026-11-06-J1C2B-CI — cross-version parity projection repair
- **Problem:** full CI `42229493643` on `617b931d` passed 976 pytest tests but failed the 01-T `legacy_semantic_digest` gate.
- **Cause:** Schema 29 added the empty `local_institutions` collection, but three cross-version parity benches did not strip it from their semantic projection. Event log and every shared semantic field were identical; only the empty new key differed.
- **Fix:** extend the three strip lists and add a regression guard in `test_knowledge_compatibility.py`. No expected digest was replaced and no parity assertion was disabled.
- **Local evidence:** 976 passed / 1 skipped on Python 3.10 and 3.13; 01-T/01-U/01-V/02-F/02-G/01-R parity restored.
- **Second stale pin:** pushed CI `42244658986` passed pytest and adversarial jobs but failed the 01-U gate on a hardcoded candidate Rules 36 assertion. Updated 01-U/01-V pins to 37 and added a guard test tied to `RULES_VERSION`.
- **Closed technically:** full CI `42246881990` and adversarial `42246881991` passed on `88c110e1` for Python 3.10/3.13. A genuine 28/36 world was refused unchanged, and a local 7-actor/38-event recovery drill passed. J1c2b-LAW, independent review and production P0 remain open.
