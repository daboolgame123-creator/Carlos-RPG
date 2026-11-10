# MIG-03 / MIG-03b — إعادة بناء ملف SQLite جديد من نسخة تاريخية حقيقية (نطاق تجريبي محدود)

**التاريخ:** 2026-11-10 UTC  
**الحالة:** `TWO_DISPOSABLE_FIXTURES_REBUILT_AND_VERIFIED / MIGRATION_TOOL_NOT_RELEASED`.  
**المصدر:** `a6c20e3edfbe85cc68819cd4fadd909472b21fd5` — Schema **41** / Rules **56**.  
**الهدف:** `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2` — Schema **42** / Rules **57**.

## نتائج دقيقة من GitHub Actions

| التجربة | نتيجة الاختبارات | المصدر الحقيقي | الهدف المستقل |
| --- | --- | --- | --- |
| مخبز + سوق 7 NPC | [#42791318864](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42791318864) **SUCCESS 3.10/3.13** | **51 حدثًا، 6 أوامر** | إعادة بناء 51 Event Receipt و6 Command Hash، وإعادة فتح الهدف و`verify()` و`snapshot()` وSQLite PRAGMAs |
| مندوب + نقل مادي + زراعة 7 NPC | [#42791885581](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42791885581) **SUCCESS 3.10/3.13** | **97 حدثًا، أمران** | إعادة بناء 97 Event Receipt و2 Command Hash، وإعادة فتح الهدف و`verify()` و`snapshot()` وSQLite PRAGMAs |

في كلا السيناريوهين:
- **الملف الأصلي لم يُفتح بوضع الكتابة أثناء إعادة البناء**؛ قرئ `mode=ro` من `sqlite3`، وتطابقت تجزئة SHA256 الأصلية قبل وبعد. أُنشئ ملف هدف جديد مستقل لم يكن موجودًا قبل العملية.
- أُنشئ عالم الهدف بواسطة `SQLiteEventStore.create_world()` في الإصدار 42/57. جُمّعت الأحداث التاريخية حسب `command_id` وتسلسلها الصحيح، وأُعيد تنفيذ كل أمر من خلال **`SQLiteEventStore.append()` الفعلي** لا عن طريق تعديل حقول إصدار SQLite. أُعيدت Flags التفويض الأصلية من سجل `commands`، ولم تستحدث أحداث/أجور/نحاسًا أو حقائق جديدة.
- تم التحقق من **التطابق الكامل للحالة الدلالية** مع عالم المصدر بعد حذف فرق رقمي Schema/Rules فقط، وتطابق جميع تسلسلات `seq/command_id/event_hash` وقيم `command_id/request_hash`. أعيد فتح الملف الهدف وفحص `verify()` الكامل واللقطة و`integrity_check/foreign_key_check`.
- لم تُحتسب نتيجة أي Python كدليل عن الآخر؛ تأكد نجاح كل وظيفة من سجل GitHub نفسه، بما في ذلك طباعة `MIG03_LIMITED_CONVERSION_PROOF` و`MIG03B_COURIER_CONVERSION_PROOF`.

## الحواجز التي ما زالت تمنع ترحيل ملف لاعب حقيقي

1. هذه التجارب **داخل GitHub Actions على SQLite مؤقت**، ولا يوجد Migrator عام معتمد أو مُتاح للاستخدام الإنتاجي؛ ليس ذلك استيرادًا تلقائيًا لملف حفظ حقيقي.
2. لم تُختبر هجرة عالم فيه عهدة نحاس شخصية قابلة للتداول، أو قرض/حقوق/إصابات/قصة أصلية/أحداث مستخدم أخرى. كل نوع غير مُثبت يُرفض بـ`UNSUPPORTED_SEMANTIC_MIGRATION` في التصميم المستقبلي.
3. لم تُنفذ بعد مصفوفة MIG-04 (Crash/الطاقة/مسار هدف موجود وسلسلة رموز/تلف WAL/تكرار الأحداث/تعدد العوالم/مزامنة/فشل نشر ذري) أو تحقق Windows/أجهزة خارجية.
4. لا تخفيف لشرط `SQLiteEventStore.load()` الحالي: لا يزال **يرفض تلقائيًا** ملف 41/56 على الإصدار 42/57. لا تغير أي تجربة فحص هذه القاعدة.
5. فتح ملف الهدف الجديد بعد إنشاء أصل جديد بواسطة SQLite لا يثبت وجود أداة نشر ذري `no-overwrite`؛ يجب تنفيذها واختبارها استقلالًا قبل اعتبار MIG-04 منتهية.

## الحكم الهندسي

**`MIG-03_PROOF_OF_CONCEPT_CLOSED_FOR_TWO_DISPOSABLE_FIXTURES`** فقط، وليس `MIG-03_GENERAL_MIGRATION_CLOSED` ولا `P0_GO`. الخطوة القادمة: بناء واجهة ترحيل صريحة ذات `dry-run + immutable source backup + target exclusive publish` وتحقق وتدقيق دلالي كامل، ثم اختبارات عدائية قبل قبول أي ملف فعلي. لا يجوز إدخالها في `load()` أو تشغيلها على عوالم محفوظة تخص اللاعب دون موافقة مستقلة.
