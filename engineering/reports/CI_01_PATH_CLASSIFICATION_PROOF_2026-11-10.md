# CI-01 — تحقق سياسة تصنيف تغييرات Git الحقيقية دون تغيير بوابات الإصدار

**التاريخ:** 2026-11-10 UTC  
**الدليل:** [Run 42789060820](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42789060820) — `SUCCESS` على SHA `db52450c1e38c99c6c0a43aeb7b3d8a45fbd1f76`.  
**الحالة:** `CLASSIFICATION_PROOF_VERIFIED / RELEASE_TRIGGER_CHANGE_NOT_AUTHORIZED`.

أنشئ workflow تجريبي مستقل [محفوظ في Git عند SHA الاختبار](https://github.com/daboolgame123-creator/Carlos-RPG/blob/db52450c1e38c99c6c0a43aeb7b3d8a45fbd1f76/.github/workflows/ci01-change-classifier-proof.yml) باسم `.github/workflows/ci01-change-classifier-proof.yml`، وأُزيل من رأس الفرع بعد نجاح التجربة لتجنب زيادة العدد الدائم للـWorkflows، دون تعديل `play47-economic-audit.yml` أو `simulation-tests.yml` أو أي check name/paths مطلوب. جلب GitHub أربع مراجعات حقيقية وقارن أشجار الملفات لتثبت أن مصنف التغييرات لا يتعامل مع وثائق قرار الإغلاق كأنها مجرد وثائق عادية.

| عينة فعلية | الملفات المتغيرة | docs-only | Full release مطلوب | حكم التجربة |
| --- | ---: | --- | --- | --- |
| `38ef004` → `1dd038` (خطط هندسية فقط) | 5 | نعم | **لا** | PASS |
| `0f8c31` → `38ef004` (وثائق قرار PLAY-47 والإغلاق) | 7 | نعم | **نعم** | PASS |
| `a6c20e` → `38ef004` (شيفرة محرك وقواعد ومواد اختبار) | 70 | لا | **نعم** | PASS |

**تصنيف أولي قابل للتطوير:** README/AGENTS والوثائق `engineering/**/*.md|json` و`simulation/docs/**/*.md` لا تشغل شرط المحرك الشامل *إلا* إذا شملت وثائق إصدار PLAY أو ROADMAP أو WORK_QUEUE؛ وأي تعديل مصدر/اختبار/Workflow أو ملف آخر يفرض مسار الإصدار. لا تعطي هذه العينة وحدها إذنًا لإلغاء الفحص عند تغيير الملفات؛ يجب اختبار ملف مختلط، وملفات workflow، والـpull-request الخاص بالدمج في وقت منفصل.

## بوابات لم تُرفع

- قراءة Branch Protection على `main` وفرع التكامل ترجع HTTP 403 في اتصال GitHub الحالي؛ قراءة repo rulesets أعادت `[]` لكنها **لا تنفي** قواعد حماية كلاسيكية. يجب التأكد من أسماء Required Status Checks قبل تغيير triggers. قد يترك `paths-ignore` لوظيفـة مطلوبة حالة Pending.
- `CI-01` هنا **إثبات تصنيف فقط**، لا حفظ لكلفة Runner جديدة بعد، ولا يعني أن workflow PLAY-47 التاريخي لم يعد إلزاميًا؛ أي SHA قرار إغلاق مستقبلًا يحتاج إعادة تحقق مطلوبة صراحة.
- لا حذف للعمل التاريخي أو للمراجعات اليدوية. عند التصميم الفعلي: حافظ على وظيفة نهائية واضحة لا تتحول إلى نجاح صامت عند تغيير كود، واختبر fail-closed/اختلاف branch/base قبل تعطيل تشغيلات ثقيلة.
- `main` وSchema/Rules وSQLite لم تتغير. P0 ما زال غير معتمد.

**الخطوة المقترحة:** `CI-01b`: طبّق policy check على PR تجريبي مختلط (docs/code/workflow)، وثبّت required-check contract مع مالك المستودع قبل أي تعديل لمشغلات full/targeted workflows.
