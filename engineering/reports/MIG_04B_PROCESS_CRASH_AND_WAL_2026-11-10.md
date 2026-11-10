# MIG-04b — قتل عملية Linux فعلًا ومنع استخدام مصدر WAL نشط

**التاريخ:** 2026-11-10 UTC  
**حكم النطاق:** `LINUX_PROCESS_KILL_PROOF_VERIFIED / GENERAL_MIGRATION_NO_GO`  
**الدليل الفعلي:** [Run #42794524369](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42794524369)، SHA `9d848b9d3615e86d8ce6268bcc4edcc127f005d4`، وظائف Python **3.10 و3.13 SUCCESS**.  
**مصدر التاريخ:** Schema **41** / Rules **56** الحقيقي `a6c20e3edfbe85cc68819cd4fadd909472b21fd5`، ملفان لعالمين مؤقتين؛ الهدف Schema **42** / Rules **57** عند `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`.  
**الأدوات التجريبية:** [mig04_adversarial_probe.py](../probes/mig04_adversarial_probe.py) و[mig04_crash_wal_probe.py](../probes/mig04_crash_wal_probe.py).

## 1. ثلاثة اختبارات SIGKILL حقيقية

| الحقن | كيف أُجري فعليًا | ما ثبته سجل GitHub 3.10 و3.13 |
| --- | --- | --- |
| `after_first_append` | إنهاء Subprocess فعليًا باستخدام `os.kill(pid, SIGKILL)` بعد نجاح أول عملية `SQLiteEventStore.append()` للهدف المؤقت | `target_published=false`، وSHA المصدر الأصلي لم يتغير |
| `before_link` | قتل Subprocess قبل `os.link(staging,destination)` مباشرة | `target_published=false`، لا ملف نهائي ناقص |
| `after_link` | قتل Subprocess بعد إنشاء Hard Link الحصري للهدف، وقبل fsync directory/تنظيف Stage | `target_published=true`، الهدف يفتح فعليًا بـ42/57 ويجتاز `verify()` والعالمين وسجل الأحداث |

جميع نتائج الوظائف تحمل علامات `MIG04B_PROCESS_SIGKILL` الثلاث، وبعدها `MIG04B_SUCCESS`. تثبت هذه التجربة مقاومة **قتل العملية في Linux أثناء تشغيل نظام ملفات عادي**، وليس مقاومة فقد طاقة أو ضمانًا عبر أجهزة تخزين مختلفة؛ بعد الربط وقبل fsync قد تختلف ضمانات الديمومة عند انقطاع الكهرباء.

## 2. مصدر لديه WAL نشط

- أُخذت **نسخة مؤقتة مستقلة** من ملف 41/56، ثم فُتح اتصال SQLite بوضع WAL مع إنشاء سجل WAL وكتابة عنصر حقيقي والتأكد من ظهور ملف `-wal` بينما الاتصال ما زال مفتوحًا.
- أُضيف إلى دالة Preflight التجريبية **رفض محافظ عند وجود `-wal` أو `-shm`**، بدل الادعاء بأن قراءة الملف الأساسي وحده تمثل Snapshot متسقًا.
- فشل التحويل كما هو مطلوب مع `ValueError`؛ لم يُنشر Target، وبقي SHA للمصدر الأصلي دون تغيير.
- لا يُعد هذا «دعمًا لـWAL» أو حلًا لسباق Writer يبدأ بعد فحص الملفات؛ يتطلب بناء **SQLite Backup API snapshot + snapshot provenance/locking** مستقلين قبل الموافقة على أي ترحيل لقاعدة حيّة.

## 3. سياق MIG-04 الأصلي

[Run #42793803908](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42793803908) نجح سابقًا في 6 حالات فساد و3 استثناءات حقن، رفض هدف موجود/رمزي، رفض أمر مكرر، ونجاح نشر عالمين و53 حدثًا/7 أوامر. [تقرير MIG-04](MIG_04_ADVERSARIAL_DISPOSABLE_PROOF_2026-11-10.md) يوثق ذلك بالتفصيل. تجربة MIG-04b أضافت **قتلًا فعليًا لعملية** وحالة WAL نشطة، دون تغيير المحرك نفسه.

## 4. قرار الموافقة والبوابات

- `MIG-04b_PROCESS_CRASH_AND_WAL_REFUSAL_VERIFIED` **لبيئة Linux الاختبارية فقط**.
- `MIG-04` **مفتوحة** للحالات المتبقية: فقد الطاقة/ديمومة عملية النشر، اختبار Windows، إعادة تجربة Wallet/Custody Copper، Snapshot Backup متسق تحت كاتب WAL نشط، اختبار ملفات متعددة العوالم/نسخ ضخمة وRollback فعلي على جهاز مستقل، ومراجعة أمنية مستقلة.
- `P0_PRODUCTION_NOT_APPROVED` ثابت؛ `migration_approved=false` في [عقد الإصدارات](../contracts/migration_41_56_to_42_57.json). لا واجهة ترحيل إنتاجية ولا ترحيل لملف حفظ حقيقي، ولا تعديل `SQLiteEventStore.load()`.
- لا تغييرات في `main`، Schema 42، Rules 57، أو كود محاكاة NPC؛ كل التعليمات والتجارب محصورة في `engineering/probes/` المؤقتة وGitHub Actions.
