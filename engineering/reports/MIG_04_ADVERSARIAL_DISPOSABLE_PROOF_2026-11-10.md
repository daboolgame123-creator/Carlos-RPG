# MIG-04 — إثبات تجريبي لفشل الترحيل الآمن، الرفض، النشر الحصري

**التاريخ:** 2026-11-10 UTC  
**الحالة:** `LINUX_DISPOSABLE_ADVERSARIAL_PROOF_VERIFIED / MIG04_NOT_FULLY_CLOSED / P0_NO_GO`  
**نتيجة CI النهائية:** [Run #42793803908](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42793803908) — **SUCCESS** على Python **3.10** و**3.13**، SHA الاختبار `aa11194e882a9c722049962d43cd2408ca5a2329`؛ سكربت الاختبار [mig04_adversarial_probe.py](../probes/mig04_adversarial_probe.py).  
**الفشل السابق:** [Run #42793658276](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42793658276) — **FAILURE** بسبب نقص `pytest` اللازم لاستيراد Fixture تاريخي؛ أُصلح التثبيت وأُعيد الاختبار على SHA جديد. هذا فشل إعداد، لا فشل المحرك.

## اختبار تاريخي حقيقي، وليس تحوير رقم الإصدار

- **المصدر المُثبت:** `a6c20e3edfbe85cc68819cd4fadd909472b21fd5`، Schema **41** / Rules **56**؛ وظيفتا Bakery/Market + عالم ثانٍ مستقل بموارد محدودة، ينتجهما كود المصدر الأصلي داخل GitHub Runner.
- **الهدف المُثبت:** `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`، Schema **42** / Rules **57**.
- **حجم التجربة:** عالمين، **53 حدثًا**، **7 أوامر** ولقطتا Snapshot فعليتان. SHA256 للمصدر في سجلَي الاختبار `21cc18f1706b5639a680fa514799b6c260b09b2b76e5482e7d6b2a5db4cef3c3`.
- **Preflight للقراءة فقط:** `sqlite3 ...?mode=ro`، `PRAGMA integrity_check` و`foreign_key_check`، فحص تجزئات أول حالة وSnapshots وEvents وإثبات تسلسل Revision/Command و`request_hash` المحسوب من أحداث/صلاحيات المصدر. كرر `dry-run` دون إنشاء هدف.
- **إعادة البناء:** يستخدم `SQLiteEventStore.create_world/append/verify/snapshot` بقواعد 42/57 وبالأحداث والأوامر والقدرات التاريخية، في ملف staging مستقل ثم نشر Linux `os.link(staging,destination)` الحصري دون استبدال موجود؛ وإعادة فتح SQLite بعد النشر ومقارنة دلالية للحالة كاملة مع استثناء Schema/Rules.
- **النتيجة:** تحقق السجلان `MIG04_SUCCESS` مع بصمة المصدر ثابتة وعدم موافقة أداة ترحيل إنتاجية.

## مصفوفة الرفض المشغَّلة فعليًا

| الفئة | حقن الخلل | النتيجة |
| --- | --- | --- |
| فساد حدث | `event.hash` غير مطابق | REJECTED، بلا إنشاء هدف |
| فجوة حدث | حذف `seq=2` من نسخة المصدر | REJECTED، بلا هدف |
| أمر مفقود | حذف سجل الأمر المصدر من نسخة اختبار | REJECTED، بلا هدف |
| فساد Snapshot | استبدال hash في Snapshot | REJECTED، بلا هدف |
| إصدار غير مطابق | تحويل `world.schema_version` في نسخة المصدر فقط إلى 42 | REJECTED |
| تزوير Capability | خفض `bootstrap` دون تعديل `request_hash` | REJECTED |
| انقطاع تجريبي | `before_rebuild` و`after_first_command` و`before_publish` | 3 REJECTED، بلا نشر هدف |
| هدف موجود أو رابط رمزي | ملف sentinel أو Symlink إلى sentinel | 2 REJECTED مع حماية المحتوى |
| تكرار أمر مغاير | `append` بنفس `command_id` وتفاصيل متغيرة | `DuplicateCommand` ولا تغيير حالة |
| إعادة نشر | تشغيل نفس المصدر على وجهة موجودة | `FileExistsError`، النسخة الجديدة لم تُستبدل |
| نجاح كامل | مصدر أصلي سليم إلى ملف هدف جديد مستقل | إعادة فتح/Replay كامل، 53 Event، 7 Commands، عالمين |

جميع نتائج الرفض تفحص غياب الهدف أو سلامة sentinel، وفحص SHA256 الأصلي. لا يساوي نجاح سيناريو الانقطاع المصطنع اختبار انقطاع طاقة حقيقي.

## قيود لا تزال تمنع إغلاق MIG-04 بالكامل

1. **Windows غير مختبر**، و`os.link` واستخدام `fsync` موثقان كبرهان Linux CI فقط، لا ادعاء قابلية نقل مباشر.
2. **لا تجارب طاقة فعلية** بعد النشر وقبل fsync / بعده أو Crash OS/عملية خارجي؛ الاستثناءات المصطنعة ليست قتل Process أو فقد طاقة.
3. **لا WAL نشط وقت النسخ** في هذا Fixture؛ البصمة تحسب ملف `.sqlite` فقط، لذلك لا نعتمدها لحالة Writer يعمل مع WAL. الفحص الأصلي `MIG-01` غطى WAL ضمن اختبارات منفصلة لكنه لا يغني عن إثبات تزامن Source أثناء هذا التحويل.
4. بعض نظم الملفات لا تدعم atomic hard-links أو Directory fsync أو تختلف semantics الخاصة بها، ولم يُختبر rollback عند فشل fsync بعد إنشاء الرابط؛ لا تصبح هذه الشيفرة Production Migrator بمجرد نجاح CI.
5. حالات حقوق الملكية والعهدة النقدية والإصابات والأحداث الزمنية المركبة/اللاعب لم تُثبت بالكامل؛ لا تمكين ترحيل شامل إلى 42/57.
6. هذا **سكربت Probe غير مُعرّض للاستخدام على ملفات المستخدم**، ولا توجد واجهة نشر/Restore إنتاجية أو سجل ترحيل نهائي أو P0 موافق عليه. حافظ على `migration_approved=false` و`SQLiteEventStore.load` الرافض للإصدارات القديمة.

**القرار:** قبول **نطاق مقاومة الفشل المُجرّب على Linux وعالمين مؤقتين** كدليل MIG-04 أولي، مع إبقاء الحالة العامة `MIG04_OPEN / P0_PRODUCTION_NOT_APPROVED`. الخطوة التالية تحقيق تزامن WAL، اختبار انقطاع Process/نشر آمن عبر أنظمة الملفات، وتحسين استعادة مستقلة خارج GitHub Runner قبل أي موافقة إنتاجية.
