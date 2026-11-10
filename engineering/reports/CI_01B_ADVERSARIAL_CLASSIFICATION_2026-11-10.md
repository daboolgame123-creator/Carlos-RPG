# CI-01b — حالات تصنيف تغييرات مختلطة مع حماية عقود الترحيل

**التاريخ:** 2026-11-10 UTC  
**الحالة:** `POLICY_PROOF_VERIFIED / REQUIRED_GATES_NOT_CHANGED`  
**الدليل:** [Run #42794930046](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42794930046) — Python **3.10 و3.13 SUCCESS**، SHA الفحص `f3c37ec614d39083330ce6ddc48c6234796c6c5e`.  
**السكربت التجريبي:** [ci01b_classifier.py](../probes/ci01b_classifier.py). لا يعدّل أي GitHub Actions قائم أو سياسة Required Checks.

## لماذا احتجنا هذا الفحص؟

تقرير CI-01 الأول تعامل مع `engineering/*.json` على أنه توثيق عادي؛ لكن **`engineering/contracts/migration_41_56_to_42_57.json` يضم قرار `migration_approved`**. هذا عقد قابل للاستهلاك آليًا، ولذلك يجب ألا تؤدي تغييره إلى تجاوز مسار مراجعة الإصدار بحجة «تعديل مستندات». عالجنا الخطر في **مصنف تجريبي فقط** دون تغيير الإنتاج.

## 14 حالة فحص اصطناعية، ثم فرق Git فعلي

| نطاق التغيير | قرار السياسة التجريبية |
| --- | --- |
| `README.md` + `engineering/INDEX.md` فقط | `DOCS_FEEDBACK` |
| تقارير `engineering/reports/*.md` فقط | `DOCS_FEEDBACK` |
| توثيق + `simulation/src/*.py` أو `simulation/tests/*.py` | `RELEASE` |
| توثيق + `.github/workflows/*.yml` | `RELEASE` |
| `simulation/docs/PLAY_*` أو `SAVE_COMPATIBILITY_POLICY.md` أو `SECURITY_POLICY.md` | `RELEASE` |
| `engineering/contracts/*.json` | `RELEASE` |
| `engineering/probes/*.py` | `RELEASE` |
| ملف غير معروف، مسار غير مأمون، أو Diff فارغ | `RELEASE` (fail-closed) |

نفّذ الفحص **14 حالة ذات توقعات مسبقة** دون أي خطأ على الإصدارين، ثم جلب رأس تكامل `1dd038d731c5072edb9eea43d29e5b3e70436d79` وقارن Git diff الحقيقي لفرع الهندسة (19 ملفًا حينئذ). النتيجة `CI01B_ACTUAL_BRANCH_DIFF` هي **`tier=RELEASE`** لأن الفرق يتضمن عقد الترحيل الآلي. هذه النتيجة أكثر تحفظًا من التصنيف الأول وهي مناسبة للتقييم الأمني.

## ما لم يحصل

- **لم تُغيّر بوابات `play47-economic-audit.yml` أو `simulation-tests.yml` أو check names**؛ لم نُخفض تكلفة أي Runner فعلية بهذه التجربة.
- Branch Protection Required Checks ما تزال قراءة GitHub API لها **403** تحت التفويض المتاح؛ لذلك لا يمكن الادعاء بأن مصنف التغييرات أصبح آمنًا للإدخال في CI الرسمي.
- السكربت نفسه دراسة **تصنيف/سياسة**؛ لا يكفي لتغيير قواعد `pull_request` أو `push` الفعلية قبل التحقق من سيناريوهات Success/Failure/Skipped والمقارنة مع required status naming.
- يجب عدم اعتبار نجاح هذا الاختبار بديلًا عن full 3.10/3.13 على SHA النهائي قبل ترقية كود أو عقد صلاحيات.

**القرار:** `CI-01B_PROOF_CLOSED_TECHNICALLY` على 14 حالة + diff حقيقي، لكن `CI-01_ACTUAL_CI_TRIGGER_OPTIMIZATION` تبقى مفتوحة حتى يصبح الوصول لسياسات الحماية متاحًا ويُنفذ إدخال check واضح يفشل بوضوح ولا يُتجاوز.
