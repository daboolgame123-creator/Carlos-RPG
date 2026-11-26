# أحدث تسليم — SAVE-01 (26 نوفمبر 2026)

أُنجزت اختبارات الاستئناف واستعادة النسخة لعالم اختبار مؤقت على الفرع المحلي
feature/carlos-save01-20261126. كود واختبارات SAVE-01 عند
d5cc7aafbac83a8573026c48d5c4da40f03f3c2c فوق PLAY-LOOP. لا توجد تغييرات محرك:
اختبار خبز جارٍ يثبت إعادة فتح المخبز وتسوية الناتج والأجر مرة واحدة عند موعدهما،
واختبار راحة جزئية يثبت عدم التعافي قبل موعد الراحة الأصلي. ملفات المصدر والنسخة
المستقلة بقيت ثابتة؛ replay وintegrity_check نجحا.

الاختبارات الموجهة: **63/63** على Python 3.12.14. الانحدار الشامل على المحتوى
المثبت في commit SAVE-01: **1944 passed, 1 skipped** على Python 3.10.22 و
Python 3.13.5. راجع تحليل SAVE-01 للتفاصيل. لم يتغير Schema46/Rules73، ولا ملفات
القصة أو الواجهة أو main. لم يُحدّث PR #185 ولم يُنشأ PR أو دمج. العمل في عالم
disposable_test=True فقط؛ P0_PRODUCTION_NOT_APPROVED والمراجعة المستقلة يظلان مفتوحين.

**الخطوة التالية:** ابدأ تحليل WORLD-01 قبل أي تنفيذ: تصميم تكوين محدود ومتسق للعالم
التجريبي ومواقع العمل والمهن، وبيان مصادر المواد والمال والطرق والأحداث التي تثبتها.
تُوسّع مهن اللاعب بعقود اختيارية موثقة، من دون تحويله إلى NPC أو بدء العمل تلقائيًا.

---

# أحدث تطوير — PLAY-LOOP (26 نوفمبر 2026)

الحالة: أُضيف فعل `PlayerGateway.work` لأول عقد خباز للاعب على الفرع المحلي المنفصل
`feature/carlos-player-baker-20261126`. رأس PR #185 الذي بُني عليه هو
`416e26b6c037b2fc504c8454d9b607aadeee7eba`، وما زال PR #185 مفتوحًا كمسودة؛
لم يُدفع أي تعديل إليه أو إلى `main`. فرع التطوير يتضمن READ-01 فوق هذا الأساس.

العقد يطلب وصفة تسمي اللاعب، الموقع الحالي، ومدخلات وأداة وأجرًا ممولين. يستهلك
البدء الحبوب الموجودة، ويضيف المنتج عند موعده، ويسوي الأجر من نقود المخبز الموجودة.
لا يحول كارلوس إلى NPC ولا يبدأ العمل تلقائيًا. اختبار الحلقة يثبت إنفاق جزء من
الأجر على طعام مخبوز محليًا، ثم أكله والراحة، مع استمرار فعل باسيم المستقل وثبات
مجموع النحاس. الإصدار Schema46/Rules73؛ يرفض Rules72 دون تعديل أو ترحيل.

الفحوص الموجهة لملف المهنة **7 ناجحة** على Python 3.10.22 و3.12.14 و3.13.5.
الانحدار الشامل Python3.10 **1941 passed, 1 skipped** خلال 24:39. الانحدار الكامل
Python3.13 **1942 passed, 1 skipped** خلال 18:14 على كود/اختبار commit
`06d61da77c2df656cd5ac672bd4fd63f5557714b`. جرى الانحدار الكامل على 3.10 قبل
إضافة اختبار حلقة الشراء/الأكل/الراحة الأخير؛ ملف المهنة النهائي كله ناجح على 3.10.
لا ملفات واجهة أو قصة تغيّرت.

كانت الخطوة التالية عند كتابة هذا القسم SAVE-01، وقد سُجل إنجازها أعلاه.

---

# READ-01 — سجل تسليم (26 نوفمبر 2026)

تم تنفيذ READ-01 محليًا على الفرع التطويري المنفصل `feature/carlos-read01-20261126`، كود التنفيذ عند `f4c795784b9f80a87ddd68794ca88bb3565168fc`، أساسه رأس NEEDS-01 `416e26b6c037b2fc504c8454d9b607aadeee7eba` بعد التحقق من أن PR #185 مفتوح كمسودة وفحوص الرأس الـ11 ناجحة. خُفّضت استدعاءات replay/SELECT للصفحة من 11/33 إلى 1/5 بلا snapshot، ولـhandoff من 21/63 إلى 1/8؛ مع snapshot 2/8 و2/11. مخرجات الصفحة والتسليم تطابقت byte-for-byte مع baseline. اختبار سباق SQLite وتاريخ المراجعة أضافا دليل اتساق.

الانحدار الكامل `python -m pytest -q`: **1935 passed, 1 skipped** على Python 3.10.22 و3.12.14 و3.13.5. تفاصيل القياس والاختبارات في [تحليل READ-01](READ_01_ANALYSIS_2026-11-26.md). التغييرات موجودة على الفرع المحلي؛ لم يُدفع فرع ولم يُنشأ PR ولم يُدمج أو يُغيّر PR #185 أو `main`.

الخطوة التالية: تحليل PLAY-LOOP واختيار أول عمل لاعب حقيقي ممول من موارد وأجر موجودين. مرشح التنفيذ هو التوصيل إذا أثبت الفحص أن المخزون والحمولة والأجر موثقة بالفعل.

---

# سجل NEEDS-01 (26 نوفمبر 2026)

اقرأ [مراجعة المشروع وخطة التنفيذ](ENGINE_REVIEW_AND_PLAN_2026-11-26.md) ثم افحص GitHub.
الفرع `feature/carlos-engine-needs-20261126` مبني فوق WEB-03 عند `985977b`؛
ثبت نجاح [CI الشامل للأساس](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45275029234).

المنفذ: حالة `player_needs` مستقلة؛ جوع يزيد بالزمن وأكل حقيقي يخفضه، وتعب وراحة30 دقيقة
تكتمل بحدث مؤقت صحيح، وواجهة عربية بأربعة مؤشرات وحجب الأفعال المتعارضة. Schema46/Rules72؛
حفظ45/71 الأصلي يرفض دون تغيير وتثبت إعادة فتحه بقارئه. السيناريوهات غير المفعلة تحتفظ بسلوكها.
نجحت اختبارات محلية3.12/3.13؛ راجع CI على رأس طلب الدمج للتأكد من الاختبارات الشاملة
والـChrome/Windows. لا تعتبر حالة `FINAL_CI_PENDING` المسجلة قبل الإرسال نتيجة نهائية.

التوجيه التالي: عالج أي فشل CI أولًا؛ ثم READ-01 لتقليل تكرار replay وعرض نتائج المهام
والذاكرة. لا تبدأ حلقة إنقاذ اقتصادي فردية؛ الاستدامة غير مثبتة، وP0 غير معتمد، و`main`
والقصة الأصلية محميان. فحوص الوكلاء ليست مراجعة خارجية مستقلة. المستخدم يفضل تقريرًا قصيرًا
وعملًا على دفعات كاملة؛ لا طلب إذن متكرر للعمل التجريبي المصرح.

---

# سجل النسخة السابقة — WEB-03 (24 نوفمبر 2026)

**مرجع قرار المالك:** `CARLOS_OWNER_DECISION_WORLD_FIRST_2026-11-23.md`؛ الأولوية لتجربة اللعب الفعلية، لا سلسلة إصلاحات جوع فردية.

**طلب المستخدم الذي عالجناه:** داخل المتصفح العربي WEB-02 كان شراء وحدة واحدة يتطلب إعادة تحميل لكل مرة، ولم تُعرض تفاصيل كلام كارلوس ورد الشخصيات. **الحل:** [Draft PR #184](https://github.com/daboolgame123-creator/Carlos-RPG/pull/184)، فرع `feature/carlos-web03-fluid-trading-dialogue-20261124` (فرع تجريبي متراكم فوق WEB-02 PR #183). ملف الدليل `simulation/docs/PLAYABLE_WEB03_FLUID_INTERACTIONS_2026-11-24.md`.

WEB-03 يوفّر اختيار كمية الشراء حتى حد المال والمخزون الحقيقي في **معاملة واحدة**، ويحدّث الصفحة جزئيًا داخل المتصفح عبر `fetch` المحلي مع إبقاء خيار النماذج القديمة إذا عُطّل JavaScript. يظهر نص اللاعب الأصلي ورد فعل NPC **السلوكي المسجل فقط** عبر `PlayerGateway.conversations()`؛ هذا ليس حوارًا حرًا مبتكرًا. أُبقيت حماية CSRF وOrigin وHost وخادم 127.0.0.1، وأصلحنا CSP للسماح `connect-src 'self'` فقط، دون اتصال خارجي.

**دليل موجه مثبت:** [Actions #45274724307](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45274724307)، **74 passed + Chromium real clicks pass** لكل من Ubuntu Python 3.10 و3.13 وWindows Python 3.13. فحص الانحدار الكامل على SHA النهائي يُتحقق منه منفصلًا. لا تُدمج PR #184 أو سابقاتها تلقائيًا. لا تتوقع حفظًا دائمًا أو جوعًا وتعبًا مفعّلين لكارلوس؛ HP وST حقيقيان في نموذج PLAY-31 والجوع/التعب غير مُحاكيين بعد.

**الخطوة التالية:** تجربة المستخدم على Windows، مع العمل داخل worktree منفصل `Carlos-RPG-WEB03` للحفاظ على مجلدات المشروع المحلية، وفحص الاستجابة والشراء والحوار. ثم نقاش احتياجات اللاعب الفعلية والتكامل قبل الانتقال إلى Isometric. لا تبدأ إصلاحات الاقتصاد الفردية مجددًا.

---

# أحدث واجهة قابلة للعب — WEB-01 (23 نوفمبر 2026)

**مشكلة مؤكدة لدى المستخدم:** Windows Terminal على Windows 10 يعرض العربية المشكولة لكن لا يعالج اتجاه RTL/BiDi صحيحًا؛ ضبط `chcp 65001` وPython UTF-8 والخطوط لم يُصلحها. لا تكرر نصائح ترميز لا تعالج السبب. [Windows Terminal RTL upstream](https://github.com/microsoft/terminal/issues/18659).

**الحل الجديد:** فرع `feature/carlos-arabic-browser-local-play-20261123`، [Draft PR #182](https://github.com/daboolgame123-creator/Carlos-RPG/pull/182)، واجهة HTML محلية بالعربية داخل المتصفح، فوق محرك القرية نفسه، بلا مكتبات إضافية أو شبكة خارجية. راجع `simulation/docs/PLAYABLE_ARABIC_BROWSER_2026-11-23.md` و`simulation/scenarios/test_village/play_village_browser.py`. تشغيلها من `simulation` عبر `$env:PYTHONPATH="src"; python scenarios/test_village/play_village_browser.py` بعد جلب الفرع. العنوان المحلي يُطبع ASCII ويُفتح في المتصفح. جلسة SQLite مؤقتة فقط؛ لا `main` ولا ملفات قصة حقيقية.

**دليل آلي مؤكد:** workflow [#45257849501](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45257849501): **65 passed لكل Windows 2022/Python3.13 وUbuntu/Python3.10/3.13**، بما فيها HTML RTL، subprocess HTTP المحلي، رفض Host/Origin/CSRF، وحركة 90 ثانية فعلية والحفظ. اختبار الانحدار الشامل على رأس PR يجب التحقق منه منفصلًا قبل الادعاء بإغلاق المهمة. لم يؤكد المستخدم بعد ظهور المتصفح بصورة صحيحة على جهازه؛ اطلب فحص تجربة الاستخدام إذا كانت هناك نتيجة جديدة.

**سياسة المالك مستمرة:** لا ندور في ترقيع الجوع الفردي؛ التجربة المرئية أولى ما لم يوجد عيب سببي عام. لا دمج تلقائي للفروع Draft.

---

# أحدث عمل قابل للعب — AR-01 (23 نوفمبر 2026)

**ابدأ من قرار المالك `CARLOS_OWNER_DECISION_WORLD_FIRST_2026-11-23.md` ثم من [دليل تشغيل كارلوس بالعربية](PLAYABLE_ARABIC_CLI_2026-11-23.md).**
بعد التوقف عن مطاردة إنقاذ كل NPC، بدأنا واجهة لعب عربية فعلية مستقلة فوق PLAY-31:
`simulation/scenarios/test_village/play_village_ar.py` — أوامر عربية ومشهد وطرق وشخصيات مرئية ومخزون كارلوس فقط. يمكن التحدث والشراء والأكل والانتظار والتحرك بحسب قوانين المحرك، دون حفظ دائم أو اختراق المعرفة. PR [#181](https://github.com/daboolgame123-creator/Carlos-RPG/pull/181) Draft مبني على PR #180 للقرار. الاختبارات الموجهة تقارن الأوامر العربية بالإنجليزية على SQLite حقيقي، والقبول النهائي يتطلب CI على آخر SHA. لا تنفذ إنقاذ جوع جديد لمجرد ارتفاع الرقم؛ استكمل قابلية اللعب تدريجيًا.

**نقطة الاستئناف:** افحص HEAD وCI في PR #181، وأغلق نطاق AR-01 إذا نجحت اختبارات 3.10/3.13 وفحوص الانحدار المطلوبة، ثم خطط لخيار واجهة مرئية عربية لاحقًا مع إبقاء المحرك مصدر الحقيقة. لا تدمج PRs إلى `main` تلقائيًا.

---

# تحديث استئناف أعلى أولوية — قرار المالك 23 نوفمبر 2026

**قبل أي عمل جديد اقرأ [قرار المالك الأحدث](CARLOS_OWNER_DECISION_WORLD_FIRST_2026-11-23.md).** جميع ملاحظات 11 نوفمبر أدناه أرشيف تاريخي؛ لم تعد عبارة «توقف عن التقدم حتى تنجو القرية كلها» سياسة التطوير. هدفنا عالم مستقل قابل للعب؛ الفقر والموت الناتجان طبيعيًا مسموحان، ولا إصلاحات متسلسلة لإنقاذ كل ساكن. أصلح العيوب السببية العامة فقط، واحفظ سلامة الأحداث والموارد والحفظ. لا دمج إلى `main`.

**آخر دليل:** P12 تقنيًا PASS #45231276040 (1876 ناجحًا ومتخطى واحد لكل 3.10/3.13)، P13 تشخيص PASS #45233765579، P14 تشخيص PASS حتى h294 #45236057906 + اختبار شامل ناجح #45236098906 (1876+1 لكل إصدار). h270→h294: الجائعون 6→9، الأعمال 105→109، الوجبات 86→89، تسليمات هدى 28→34؛ التشغيل مستمر لكن **الاستدامة غير مثبتة**. PRs #177–#179 Draft، لا دمج. فرع التوثيق: `docs/carlos-world-first-progress-decision-20261123`. الإجراء التالي: مراجعة محدودة لعيب مشترك حاسم واحد إن ثبت، وإلا توثيق حدود PLAY48 والتقدم نحو تجربة اللعب؛ لا سلسلة P15/P16 لإنقاذ أفراد.

---

# كارلوس RPG — قرار إنهاء دورة PLAY-48 (11 نوفمبر 2026)

**لا تبدأ PLAY-49 أو تجارب PLAY-48 جديدة تلقائيًا.** `PLAY48_EXECUTION_ENDED / PLAY48_ACCEPTANCE_FAILED / RELEASE_NO_GO`. أُنجزت مكونات تكرار الإنتاج والنقل تقنيًا، لكن **شرط الاستدامة الاقتصادية للمرحلة فشل**، ولذلك هذه نهاية دورة تجريبية بنتيجة سلبية، **وليست** `PLAY48_CLOSED_TECHNICALLY`.

**أدلة محسومة:** [قواعد 61، 1696×2 اختبار كامل ورغيفان فعليان للمزرعة #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) SUCCESS Python3.10+3.13، مع ثبات 12 نحاسًا ورفض حفظ Rules60 القديم دون تعديل. [محاكاة الاستدامة 96 ساعة #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) أثبتت جوع **13/13** وتوقف النقل والأعمال والوجبات والمبيعات بعد الساعة72. لا تغطية للانهيار ولا ادعاء بقاء 168 ساعة.

**المستودع والنسخ:** `integration/play48ac-rules61-verified-20261111`، شيفرة المحرك المختبرة `e3db72d8584de1076b78ebba27cfe4c82714235a`، Schema45/Rules61 تجريبيان، `main` دون تغيير، ولا ترحيل للحفظ. المراجعة المستقلة مؤجلة بقرار المالك ولم تُجرَ.

**ما يترتب عليه:** لا استمرار تلقائي في PLAY-48 ولا انتقال PLAY-49 قبل قرار مالك مستقل يعالج شرط التعافي الاقتصادي أو يعيد اعتماد نطاق المرحلة. [ملف قرار المرحلة النهائي](PLAY_48_PHASE_TERMINAL_DISPOSITION_2026-11-11.md) هو المرجع الأعلى، والقوائم القديمة تاريخية.

---

## Final verified acceptance update — 2026-11-11

**`PLAY48_TRANSPORT_CLOSED_TECHNICALLY / PLAY48_ECONOMY_NO_GO / RELEASE_NO_GO`**. The authoritative [final acceptance record](PLAY48_FINAL_BOUNDED_ACCEPTANCE_AND_STOP.md) supersedes older PENDING declarations in the historical sections below.

[Exact-head Rules61 CI #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) **SUCCESS** Python3.10+3.13: **1,696 historic tests passed in each version**, both actual 13-NPC 48h A/B jobs PASS, real grain share produced **3 entitlements and 2 genuine bakery→farm delivered loaves**, market stock **7→5**, all **12 copper conserved**, and old 45/60 saved worlds rejected with unchanged bytes. [Original independent AC #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878) also **SUCCESS** both versions. The bounded transport investigation is **CLOSED**; don't reopen it or invent a payroll fix.

**Explicit remaining phase-wide blocker:** [96h #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) proves 13/13 starving by day4 and zero new work/deliveries/meals after hour72; no new farm wage funding, seven-day recovery, migration, release, or `main` merge. Treat future economic sustainability as a separate approved scope. No PLAY49 until a separate phase decision.

---

# Carlos RPG — قرار إيقاف توسّع PLAY-48 وإغلاق مهمة النقل ضمن شروطها

**11 نوفمبر 2026.** المستخدم طلب إنهاء المهمة المطوّلة، لذلك **لا تبدأ تجارب اقتصادية جديدة بلا قرار مستقل**. الحالة: `PLAY48_TRANSPORT_IMPLEMENTED_REAL_POSITIVE_PY313 / DUAL_ACCEPTANCE_PENDING`. و`PLAY48_ENDURANCE_NO_GO / MAIN_NO_MERGE`. 

**النجاح المؤكد:** [PLAY48AC 48h CI #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878) Python3.13 نجح واقعيًا في 13 ساكنًا: **2 رغيف** انتقلًا من المخبز إلى المزرعة، **3 استحقاقات** بعد توصيل القمح، **12 نحاسًا محفوظًا**، السوق أصبح لديه **5 أرغفة بدلًا من 7**، ولم تتغير الوجبات العامة (6) خلال اليومين. هذا انتقال مادي حقيقي، لا حل لتمويل أجر هدى تلقائيًا ولا استقلال غذائي لأسبوع. Python3.10 الفعلي بقي يعمل عند آخر فحص.

**التوافق:** قواعد النقل الجديدة المنفصلة **Schema45/Rules61**. [اختبارات Rules61 #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) نجاح الفحوص السريعة ورفض حفظ Rules60 الأصلي دون تغيير بايت على Python3.10+3.13، لكن الانحدار الكامل ومحاكاة 48 ساعة على الكود النهائي ما زالا قيد التنفيذ. [الانحدار Rules60 السابق #43037819648](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037819648) **1696 اختبار ناجح على كل إصدار**، ولا يحل محل اختبار Rules61. فرع التكامل `integration/play48ac-rules61-verified-20261111`، `main` لم يتغيّر.

**سبب عدم إعلان اكتمال اقتصاد PLAY48:** [محاكاة أجور هدى 96h #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) أثبتت **13/13 جائعين في اليوم الرابع** وصفر أعمال أو وجبات أو نقل بعد الساعة72. لم ننفذ تجديدًا آمنًا لأجورها من مخزون المزرعة، ولم نثبت بقاء القرية 168 ساعة. لا تزعم إغلاق PLAY48 اقتصاديًا، أو إصدار جاهز، أو ترحيل حفظ، أو دمج في main.

**قاعدة الإيقاف:** ما تبقى فقط قراءة CI الحالية والإبلاغ؛ إذا نجحت جميعها يجوز توثيق `PLAY48_TRANSPORT_CLOSED_TECHNICALLY` ثم تجميد مهمة النقل. استدامة الدخل والغذاء مشروع قرار مستقل لاحقًا وليس سلسلة لا تنتهي من تجارب PLAY48. التقرير الرسمي [PLAY48_FINAL_BOUNDED_ACCEPTANCE_AND_STOP.md](PLAY48_FINAL_BOUNDED_ACCEPTANCE_AND_STOP.md).

---

# Carlos RPG — أحدث نقطة مؤكدة: PLAY48AC / Rules61 (11 نوفمبر 2026)

**الحالة:** `PLAY48_OPEN / RELEASE_NO_GO`، لا دمج في `main` ولا ترحيل للحفظ القديم ولا بدء PLAY49. عند الاستئناف افحص GitHub CI مباشرة؛ هذا المستند سجل بتاريخ ثابت.

### حقائق مؤكدة من الاختبارات

- [PLAY48AB محاكاة 48 ساعة #43037662900](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037662900) **FAILED Python3.10 +3.13** في العالم الحقيقي: `pickup must use the local planned shipping lane`. السبب مشخص في فرق نوع الحمولة: مُقرر النقل يختار FOOD في رجعة المخبز→المزرعة (index4) لكن LivingWorld كان يرسل حدثًا بموارد COPPER من خريطة أرقام قديمة. تمسك الـReducer بمنع الحمولة الوهمية كان سلوكًا صحيحًا.
- **PLAY48AC إصلاح فعلي:** محرك النقل الآن يخرج `choose_cargo_manifest` (الفعل + نوع الحمولة من المسار الحقيقي ذاته)، ولا يستنتج نوع البضاعة من رقم المحطة. فرع الكود `experiment/play48ac-authoritative-cargo-manifest-20261111`، SHA المختبَر `c9577d9870799d2f8b57db73416f663bb1b796cc`. [فحص #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878) **الاختبارات السريعة ناجحة على Python3.10 و3.13**. محاكاة القرية الفعلية لـ48 ساعة ما زالت جارية عند كتابة المستند؛ لا تدّعِ وصول أي رغيف قبل قراءة `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD`.
- **حماية الحفظ الجديدة:** فرع التكامل `integration/play48ac-rules61-verified-20261111` يحافظ على Schema45 ويصعد إلى **Rules61**، حتى لا تحمل ملفات Rules60 المعنى الجديد بصمت. [CI #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) فحوص الحمولة السريعة واختبار حفظ 45/60 الحقيقي والرفض دون تغيير بايتات ناجحة على الإصدارين. الاختبار التاريخي الكامل وتجربة 48 ساعة على *Rules61 ذاته* كانا قيد التنفيذ؛ لا تعلن نجاحهما قبل ظهور سجلاتهما.
- [الانحدار السابق 45/60 #43037819648](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037819648) **1696/1696 ناجحة لكل إصدار** Python3.10 و3.13 بعد إعادة اختبار انتظار جزئي إلى 59 ثانية الصحيح؛ لا تغطي هذه النتيجة Rule61 الجديد.
- [PLAY48Y2 محاكاة الأجور 96 ساعة #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) ناجحة تقنيًا على الإصدارين لكنها تثبت الانهيار: هدى سلمت12 مقابل3، الأعمال24 مقابل20، الوجبات7 مقابل5؛ **13/13 الجوع100** بحلول اليوم الرابع، **صفر أعمال وتوصيلات ووجبات وصفقات بعد الساعة72**. المأزق دخل وتوزيع وغذاء وليس مجرد قمح.

### القرار التالي بعد الاختبار

1. افتح [CI Rules61 #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) و[AC #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878)، وافحص القيم الفعلية `actual_bread_returned_to_farm` و`grain_entitlements_after_real_grain_deliveries` ومقارنة مخزون المخبز والسوق والنقود. الاختبارات الخضراء وحدها لا تثبت وصول الخبز.
2. إذا وصل خبز فعليًا إلى المزرعة، يجب تمويل أجر هدى من هذا المخزون **بعد توثيق ملكية المزرعة وموافقة رب العمل وخدمة ماء جديدة مثبتة**. لا استهلاك لحمولة الأمانة ولا دفع مكرر أو رجعي، ولا توليد خبز/نحاس.
3. تبقى مبادلة 1 قمح = 1 خبز تجريبية وغير مؤكدة اقتصاديا؛ قارن كلفة الخباز والوقود وأثرها على مبيعات السوق قبل اعتمادها. اختبر العجز المالي والجفاف و96/168 ساعة و13 شخصية مستقلة ونسخ الحفظ.
4. **لا تدّعِ إغلاق PLAY48، ولا تدمج في main، ولا تبدأ PLAY49.**

المستند المفصل: [PLAY48AC_RULES61_AUTHORITATIVE_CARGO_AND_RECOVERY.md](PLAY48AC_RULES61_AUTHORITATIVE_CARGO_AND_RECOVERY.md). قائمة الحالة: [WORK_QUEUE.md](WORK_QUEUE.md).

---

# Carlos RPG — latest PLAY-48AA integration handoff (2026-11-11)

**Status:** `PLAY48_OPEN / RELEASE_NO_GO`. `main` untouched, no old-world production save migration or 168h recovery acceptance. **Verify GitHub CI status/live SHA before continuing**; this file is a dated record.

Current verified physical facts: 13 genuine NPCs, 12 conserved copper, only 3 real initial loaves, farms grow with finite water and time. [Huda genuine two-farm-wage 48h #43017271741](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741) SUCCESS 3.10/3.13: Huda ate 2 and transported 10 instead of 3 deliveries, hunger86 vs100. [Hana capped market-food 96h #43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657) SUCCESS as a **NEGATIVE economic result**: both A/B worlds 13/13 hunger100 and ZERO new work, food sales, meals or transport after hour72. A 48h positive wage result is not village survival. [PLAY48Z actual road proof #43028314540](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028314540) SUCCESS: existing bakery→farm road returned copper only, without legitimate bread procurement.

**Active new code:** `experiment/play48aa-physical-grain-for-bread-return-20261111`, tested core SHA `4b4c8b663ead5fa5483d23e8b9dee195777d6200` using **experimental Schema45 / Rules60**. Trusted time-zero circuit option `farm_bread_share=True` earns one bread entitlement after actual physical grain delivery to the bakery. It does NOT mint bread. Courier can use existing bakery→farm return leg to carry a genuinely baked, bakery-owned, unquoted/unconsigned loaf (and keep one bakery spare), **OR** copper, never both. Delivery physically credits farm food and settles exactly one claim. Alternating potential cash and bread trips can delay legitimate farm copper wages. Current 1 raw grain : 1 finished bread ratio is an **unreviewed generous experimental price**, not evidence of a profitable local economy; inspect actual bakery and market costs before production.

**Evidence:**
- [PLAY48AA targeted run #43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266) signed genesis/forgery checks **PASS both Python3.10/3.13**, but **true actual 48h 13-NPC A/B remains pending**. Read `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD` log before claiming positive freight. First run failed overly strict t=0 slot-order check, fixed and rerun.
- [PLAY48AA security CI #43034249899](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43034249899) **SUCCESS 7 tests each Python3.10+3.13** in an independent version-contract integration branch: customer quote protection, alternating copper/food, no duplicate cargo or bakery food rights, tampering blocked.
- [PLAY48AA Schema45/Rules60 complete prior-tests and real old save gate #43033787068](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43033787068) **real old44/59 SQLite save rejection without any byte mutation PASS both 3.10/3.13**. Full historical regression is **pending**; newer source on branch `integration/play48aa-schema45-regression-20261111`, initial workflow SHA `a9001058c18831cad5e7ef73b5deb5bad0b2c930`. 23 historic test files' current-world pin updated 44/59→45/60; explicit old43/58 rejection fixture unchanged; 6 active test-world version pins updated. Do not call full suite green until both jobs finish.
- [Y2 genuine 96h farm wage/13 professions #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) independently running older Schema44/Rules59 scenario; read its per-occupation personally owned cash and after72 jobs/deliveries/meals.

**Next priority:** finish **AA real 48h** and 45/60 exact-SHA full tests; if grain return truly delivers bakery bread, separately implement PRE-SIGNED farm employer procurement and **legitimate wage escrow refill** after physical farm food arrival and only on genuine Huda service, never from worker's consigned food. Assess bakery economic loss from 1:1 barter before deciding permanent ratio. Then authentic 96/168h same-genesis full-village survival, drought/bankruptcy and migrations, without relaxing hunger>=90 safety. The [detailed decision](PLAY48AA_INTEGRATION_SECURITY_AND_RECOVERY.md) and [WORK_QUEUE.md](WORK_QUEUE.md) are linked.

---

# Carlos RPG — confirmed newest tasks (2026-11-11, PLAY-48)

**Source of truth remains exact GitHub CI and git SHA, not this static handoff.**

## Official status

- **PLAY48_OPEN / RELEASE_NO_GO**. Do not touch `main` or begin PLAY49. No production migration of old SQLite saves, no claim that the village has survived a true 168-hour recovery.
- Current experimental code **Schema 44 / Rules 59**, new market service salary events/contract ceiling. Old validated saves remain Schema43 / Rules58; latest code rejects them safely rather than automatically migrating.
- Carlos world sim operates on actually tracked 13 residents, 12 copper, 3 opening loaves, bounded seed/water/rain, true crop maturity, physical roads, no magical transfers.

## Completed verified runs

| Scope | Run / exact SHA | Result |
| --- | --- | --- |
| PLAY48W — two actually signed market employee contracts | [#43007695830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007695830), `c9f7c4309e392996da19a361fb1dbebe0c0cffb3` | **SUCCESS both Python 3.10/3.13 real 48h**. Hana eats two extra employer-funded loaves and hunger improves; Huda earns **zero** market wages because her physically actual farm-water work doesn't satisfy the market food-delivery condition. |
| PLAY48U — Hana market contract, real new salaries | [#42999941836](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42999941836), `81b8446a` | **SUCCESS both**. Genuine 2 extra Hana wages, 6→8 village meals, hungry100 5→4, Hana hunger100→60, **no increase in 35 actual deliveries**, 12 copper conserved. |
| PLAY48X — current-version historic regression and save rejection | [#43014260381](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43014260381), tested source `b939992d9d342175d042cb206e4c545fc4ea2a15` | **SUCCESS Python3.10 and 3.13: 1696/1696 pytest each**, after explicitly updating 23 current-version test files and two current Rules59 pins. Genuine old 43/58 save verified with frozen old SHA `aa836e46...`, then rejected by 44/59 **byte-for-byte untouched**. This proves rejection, NOT migration. |
| PLAY48S3 — prior 96h one-off wages | [#42926808427](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42926808427) | **SUCCESS dual-Python negative economic finding**: 13/13 starvation and zero post72 jobs, deliveries and meals. |

## Current pending genuine experiments

- **PLAY48V — real 96-hour renewable-but-capped Hana market wages**: [#43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657), tested source `37cd8fb5a1d5fed140a3c5d9ec19b4cac164e0a3`, *two long jobs in progress at last check*. Need inspect `PLAY48V_TRUE_FOUR_DAY_MARKET_WAGES_CAUSAL_PROOF` before claiming post72 recovery or negative.
- **PLAY48Y — bounded Huda farm-worksite wage trial**, current branch `experiment/play48y-farm-worksite-paid-courier-20261111`. [#43017271741](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741), tested source SHA `81cddebbc738832c2409f603f38d2fb6f805eca4`. **Both Python genesis checks PASSED**, true 24/48h independent A/B still in progress. Genuine same 13NPC worlds: only 3 opening real loaves, but time-zero ownership is now **2 FARM + 1 MARKET** rather than historical **1 FARM + 2 MARKET**; Huda's farm employer escrows 2 of its originally owned bread for physically delivered water, control vs early pay identical at genesis. This tests finite actual worksite nutrition without inventing wages, food, routes or resources. First attempt failed because bootstrap was incorrectly treated as an event-transformer; corrected by adding bounded `farm_initial_food_loaves=2` to the existing test-world initializer, which defaults to 1 on all original scenarios. **Do not claim the extra wages are paid/eaten before checking actual long tests**.
- More details: [PLAY48Y_FARM_HUDA_PAID_WORKSITE_TRIAL.md](PLAY48Y_FARM_HUDA_PAID_WORKSITE_TRIAL.md).

## Next

1. Check actual live results of V and Y, compare Huda hunger, real deliveries, Hana wages, personal food consumption, market bread rights, all 12 copper, and SQLite replay.
2. If Y provides a benefit, **do not mistake preexisting extra farm bread for renewable supply**. A genuine long-term worksite wage requires physically procured bread delivered to FARM by a valid courier, with explicit farm ownership (purchase/barter), real site arrival, and no consumption of customer-quoted or entrusted food. New transport policy may demand new version/migration and full review.
3. Need actual non-courier income and food access for 11 other villagers; later genuine 96/168h A/B under bounded rain, drought, insolvency, with post72 work/delivery/meals documented.
4. Full CI and save rejection at exact final integrated source, independent review. Do not merge or claim closure in this chat without those proofs.
