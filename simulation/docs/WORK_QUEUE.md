Warning: truncated output (original token count: 44026)
Total output lines: 1783

# Carlos RPG — سجل توجيه الأعمال القابلة للاستئناف

## الحالة الحالية — 28 نوفمبر 2026

المرجع الأحدث: [مراجعة الأنظمة وخطة التنفيذ](ENGINE_REVIEW_AND_PLAN_2026-11-26.md).
WEB-03 عند `985977b` اجتاز [الانحدار النهائي](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45275029234).
قرار [العالم أولًا](CARLOS_OWNER_DECISION_WORLD_FIRST_2026-11-23.md) يقدّم حلقة اللعب
على شروط الإنقاذ الاقتصادي التاريخية أدناه. لا إعادة P11–P14.

| ID | المهمة | الاعتماد | التصنيف | الحالة عند الإيداع | الدليل/الخطوة التالية |
|---|---|---|---|---|---|
| NEEDS-01 | احتياجات كارلوس وأكل وراحة فعلية وواجهة عربية | WEB-03 أخضر | READY_FOR_VERIFICATION | LOCAL_VERIFIED / FINAL_CI_PENDING | Schema46/Rules72، اختبارات محلية وتوافق أصلي؛ فحص آخر SHA في PR الفرع `feature/carlos-engine-needs-20261126` |
| READ-01 | تقليل replay المتكرر وعرض نتائج الأوامر | NEEDS-01: PR #185، رأس `416e26b6c037b2fc504c8454d9b607aadeee7eba` وفحوصه الـ11 ناجحة | CHAT_EXECUTABLE | CLOSED_TECHNICALLY / LOCAL_VERIFIED، كود `f4c795784b9f80a87ddd68794ca88bb3565168fc` على `feature/carlos-read01-20261126`؛ Python 3.10/3.12/3.13: 1935 passed + 1 skipped | [تحليل ونتائج 26 نوفمبر](READ_01_ANALYSIS_2026-11-26.md)؛ التالي تحليل PLAY-LOOP |
| PLAY-LOOP | عمل حقيقي مدفوع للاعب — خبّاز | READ-01 محقق محليًا؛ عقد المهنة والتمويل | CHAT_EXECUTABLE | IMPLEMENTED / LOCAL_VERIFIED على `feature/carlos-player-baker-20261126`، كود/اختبارات `06d61da77c2df656cd5ac672bd4fd63f5557714b` | [تحليل ونتائج 26 نوفمبر](PLAY_LOOP_ANALYSIS_2026-11-26.md)؛ 3.13 كامل: 1942 passed + 1 skipped؛ 3.10 كامل: 1941 + 1 skipped قبل اختبار التكامل الأخير، وملف المهنة النهائي 7/7 على 3 إصدارات |
| SAVE-01 | استئناف القرية واستعادة نسخة | عقد إصدار مثبت | CHAT_PARTIAL_EXTERNAL_GATE | LOCAL_VERIFIED / FULL REGRESSION GREEN: 1944 passed + 1 skipped على Python 3.10 و3.13 | [تحليل ونتائج SAVE-01](SAVE_01_ANALYSIS_2026-11-26.md)، الاختبارات الموجهة 63/63 على Python 3.12؛ P0 والمراجعة المستقلة مفتوحان |
| WORLD-01 | تكوين العالم التجريبي والمهن والمواقع | SAVE-01 موثق تقنيًا؛ دون اعتماد حفظ إنتاجي | CHAT_EXECUTABLE | IN_PROGRESS — W01d/e/f/g/h/i/j مغلقة تقنيًا؛ W01k `CLOSED_TECHNICALLY / EXACT_SHA_FULL_CI_PASS`؛ المراجعة المستقلة مؤجلة بقرار المالك؛ WORLD-01 الأوسع وP0 الإنتاجي مفتوحان | [تحليل W01k](WORLD_01K_PLAYER_WOODCUTTER_ANALYSIS_2026-11-28.md)؛ الاختبار الجديد 1/1 في 0.67s والرجوعيات القريبة 8/8 في 8.29s محليًا على Python 3.12.14. CI على SHA `dd821768d7b7df1728b338e24c0821f7fc15329b`: [المحاكاة #46125619450](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/46125619450) نجحت في 3.10 و3.13، 1,963 passed + 1 skipped لكل منهما، و90/90 خطوة لكل وظيفة؛ [NEEDS #46125619433](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/46125619433) نجح في Linux 3.10/3.13 وWindows 3.13. لا تعديل لمحرك الإنتاج أو Schema/Rules. التالية CAREER-01 أُغلقت؛ ابدأ تحليل تجارب استقلال الشخصيات |
| CAREER-01 | اختيار كارلوس من المهن الموثقة | دورتان حقيقيتان (PLAY-LOOP + W01k) معتمدان على CI | CHAT_EXECUTABLE | CLOSED_TECHNICALLY / EXACT_SHA_FULL_CI_PASS / EXTERNAL_REVIEW_DEFERRED_BY_OWNER | [تحليل ونتائج 28 نوفمبر](CAREER_01_ANALYSIS_2026-11-28.md): عقد الخباز والحطاب موجودان في `production_recipes` والاختيار الصريح عبر `work(recipe_id)`. الاختبار الجديد يختار العقدين في عالم واحد ويرفض غير المتاحين ذريًا. محليًا 9/9 في 2.19s؛ على SHA `89402cbbdb0add710cf693c2f7d0d6f9b599d45b` نجح [CI المحاكاة #46132604026](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/46132604026) بـ1,964 passed + 1 skipped على 3.10 و3.13 (90/90 لكل وظيفة)، و[NEEDS #46132604019](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/46132604019) على Linux/Windows (13/13 لكل وظيفة). بلا تغيير لمحرك الإنتاج أو Schema/Rules. التالي تحليل المرحلة 7 لتجارب استقلال سلوكي صغيرة. |
| WORLD-02-SCENARIO | تكامل استقلال سلوكي محدود | CAREER-01 أخضر على `89402cbbdb0add710cf693c2f7d0d6f9b599d45b`؛ لا اعتماد إنتاجي | CHAT_EXECUTABLE | IMPLEMENTED / LOCAL_FULL_PASS / EXACT_SHA_CI_PENDING | [تحليل ونتائج 28 نوفمبر](WORLD_02_SCENARIO_ANALYSIS_2026-11-28.md): اختبار 7 NPC على SHA `2bc76726f3a132f6e1dc01da01e3bdaa865cd482`؛ الموجه 98/98 في 16.67s، والانحدار المحلي Python 3.12: 1,964 passed + 1 skipped في 815.70s. لا تعديل لمحرك/Schema/Rules/قصة. المطلوب التالي: CI Python 3.10/3.13 على رأس PR #186 بعد نشره. |
| CI-03-SCALE | قياس توسع العالم متعدد القطاعات قبل تحسين المحرك | تدقيق CI-03؛ نتائج A/B سابقة؛ دون تغيير قواعد أو بيانات العالم | CHAT_EXECUTABLE | CLOSED_TECHNICALLY / EXACT_SHA_FULL_CI_PASS (external review deferred by owner) | المعيار `bench_realistic_world_scale.py` عند كود SHA `d399ffc970b139a5359208cf7c9fb8ee80395dd8`؛ قياسات 1/2/4/8 قطاعات (4–32 NPC)، و16 قطاعًا/64 NPC على successor توثيقي بنفس ملف القياس، مع تكرارين وبصمات موارد/حالة/حدث متطابقة وreplay/snapshot/integrity. CI [#46080863733](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/46080863733) نجح على SHA الدقيق: 1,958 passed + 1 skipped لكل Python 3.10/3.13؛ 90/90 خطوة لكل وظيفة بلا فشل. 96h والسوق المشترك لم يكتمل قياسهما؛ CI-03 الأوسع ما زالت جزئية. PERF-01 مغلق؛ PERF-02a وPERF-02b لهما نتائج وتغييرات محلية، وCI النهائي مطلوب. [نتيجة PERF-02b](../../engineering/PROJECTION_COPY_PERFORMANCE_ANALYSIS_2026-11-28.md). |
| PERF-01-FREEZE | مسار سريع للقيم البدائية داخل تجميد إسقاطات الأحداث | تحليل CI-03-SCALE؛ الحفاظ على تحقق الإسقاط والحتمية | CHAT_EXECUTABLE | CLOSED_TECHNICALLY / EXACT_SHA_FULL_CI_PASS / EXTERNAL_REVIEW_DEFERRED_BY_OWNER؛ الكود `ec742b6bce77fa37ea83e0b17584c8cc3781a9d8`، CI على SHA `3e7bb653554e84d5bb7264b627aa362dbb07ce89` | `_freeze` يعيد أنواع JSON البدائية الدقيقة مباشرة ويُبقي تجميد القواميس/القوائم والترتيب ودعم الأنواع الفرعية. 36/36 اختبارًا موجّهًا؛ بصمات السجل والحالة متطابقة في معيار 1–16 قطاعًا. CI [#46084550760](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/46084550760): 1,959 passed + 1 skipped على Python 3.10.22 و3.13.18؛ 90/90 خطوة ناجحة لكل إصدار. cProfile التشخيصي خفّض الكلفة التراكمية لـ`_freeze` من 19.093s إلى 12.998s؛ قياسات الزمن العادية لا تثبت مكسب سعة. يليه PERF-02-PROJECTION-COPY لتحليل نسخ الإسقاطات وتحسينات validators الموضعية. التفاصيل: [تدقيق CI والأداء](../../engineering/CI_PERFORMANCE_AUDIT_2026-11-27.md). |
| PERF-02-PROJECTION-COPY | تحليل كلفة نسخ الإسقاطات والتحقق لكل حدث | PERF-01 مغلق؛ cProfile ومعيار العالم | CHAT_EXECUTABLE | IMPLEMENTED / LOCAL_TARGETED_PASS / BENCHMARK_HASH_EQUIVALENT / EXACT_SHA_FULL_CI_PASS / GENERAL_COW_NO_GO | فهرسة محلية كسولة لأصحاب الأفعال الجارية والمسافرين داخل `validate_production_state`؛ 18/18 اختبارًا وقياس العالم 4–32 NPC محفوظ البصمات. PERF-02b: معيار مستقل لعقد أجر تاجر وموارد افتتاحية معلنة؛ 16 إيصالًا/32 صفقة: مسح `_earned_sales` هبط 18,744→272 صفًا؛ 32 إيصالًا/64 صفقة: 151,408→1,056. عند 32 إيصالًا و7 تكرارات انخفض وسيط الإضافة 0.322→0.245s وreplay 0.315→0.248s؛ تطابقت هويات الصفقات والعروض وحُفظت الأرصدة ونجح replay. أضيف فهرس زمني مؤقت داخل التحقق، بلا تخفيف لأي عقد أو تغيير Schema/Rules. اختبار الأجر 15/15 وmarket 02c 15/15 محليًا. CI الكامل نجح على SHA `3b2ede6bc2ddbe93c5e06b41137693bfdb0789d2`: #46123284255 في Python 3.10/3.13 ووظائف NEEDS/المتصفح #46123284215؛ لا ادعاء بسعة عامة. PERF-02 وW01k وCAREER-01 مغلقة تقنيًا؛ التالي تحليل WORLD-02-SCENARIO. [التقرير والمنهج](../../engineering/PROJECTION_COPY_PERFORMANCE_ANALYSIS_2026-11-28.md). |


الأقسام التالية سجل تاريخي؛ لا تتقدم على الحالة الحالية أو سياسة المالك.

## إعادة فتح PLAY48 بأمر المالك — 2026-11-16

`PLAY48-INCOME-INTEGRATION | إصلاح الدخل والأكل والنقل المترابط | PR133/134/135 | CHAT_EXECUTABLE | IN_PROGRESS | Windows + GitHub Actions | base 1e04e84 | انتظار A/B وCI النهائي | إصلاح أول بوابة فاشلة ثم 96/168h`.
تحديث17 نوفمبر: المرشح Rules70 عند `f6b124d` اجتاز الانحدار الكامل
[43878111956](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43878111956)
لكلا الإصدارين، لكنه فشل بوابة60h: لا أجر/شراء/وجبة لنورا.
مرشح Rules71 يصلح انتظار الساعيات ويربط شراء القمح المسبق بنحاس منقول
فعليًا إلى مصدره؛ **33 اختبارًا موجهًا محليًا لكل3.10/3.13**، حالة
`READY_FOR_VERIFICATION / PLAY48_NO_GO` بانتظار CI وA/B على HEAD الجديد.
التفاصيل: [التقرير التكاملـي](PLAY48_INTEGRATED_INCOME_2026-11-16.md).
هذا القرار أحدث من إنهاء الدورة أدناه؛ النتيجة الحالية `PLAY48_NO_GO` حتى الإثبات.

## PLAY-48 — final execution termination decision (2026-11-11)

**Latest authoritative status: `PLAY48_EXECUTION_ENDED / PLAY48_ACCEPTANCE_FAILED / RELEASE_NO_GO`**. Bounded production and real bakery→farm transport features are **verified complete**; phase-wide 13-NPC multi-day economic recovery is **failed**. The old historical OPEN/PENDING lines below are archival and superseded by this terminal decision, **not** authorization to close the phase as technically passed. No more PLAY48 iterations unless a new owner decision explicitly reopens or changes this blocked scope.

| Final gate | Evidence / decision |
| --- | --- |
| Real workshop, smelting, construction and repair iterations | [#42808944705](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42808944705), [#42809457769](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42809457769), [#42812662593](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42812662593) SUCCESS both Python |
| Final Rules61 freight, real 2 bakery→farm loaves, historic suite 1696×2, genuine old-save rejection | [#43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) SUCCESS |
| 96h living 13-NPC economy acceptance | [#43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) NEGATIVE: all 13 hunger100, zero post72 work, transport, eating or sales |
| Stage advance and production | `PLAY49_NOT_AUTHORIZED / MAIN_UNCHANGED / P0_PRODUCTION_NOT_APPROVED` |

[Full terminal decision](PLAY_48_PHASE_TERMINAL_DISPOSITION_2026-11-11.md).

---


## Final verified acceptance update — 2026-11-11

**`PLAY48_TRANSPORT_CLOSED_TECHNICALLY / PLAY48_ECONOMY_NO_GO / RELEASE_NO_GO`**. The authoritative [final acceptance record](PLAY48_FINAL_BOUNDED_ACCEPTANCE_AND_STOP.md) supersedes older PENDING declarations in the historical sections below.

[Exact-head Rules61 CI #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) **SUCCESS** Python3.10+3.13: **1,696 historic tests passed in each version**, both actual 13-NPC 48h A/B jobs PASS, real grain share produced **3 entitlements and 2 genuine bakery→farm delivered loaves**, market stock **7→5**, all **12 copper conserved**, and old 45/60 saved worlds rejected with unchanged bytes. [Original independent AC #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878) also **SUCCESS** both versions. The bounded transport investigation is **CLOSED**; don't reopen it or invent a payroll fix.

**Explicit remaining phase-wide blocker:** [96h #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) proves 13/13 starving by day4 and zero new work/deliveries/meals after hour72; no new farm wage funding, seven-day recovery, migration, release, or `main` merge. Treat future economic sustainability as a separate approved scope. No PLAY49 until a separate phase decision.

---



## PLAY-48 bounded transport termination decision — 11 Nov 2026

**Do not reopen endless PLAY48 wage/transport experiment branches.** This bounded transport task has a real positive Python3.13 outcome and is only waiting on existing CI acceptance gates, not new simulation features. [PLAY48_FINAL_BOUNDED_ACCEPTANCE_AND_STOP.md](PLAY48_FINAL_BOUNDED_ACCEPTANCE_AND_STOP.md)

| Scope | Decision | Source |
| --- | --- | --- |
| Signed 13-NPC physical bakery→farm shipment | **REAL_POSITIVE_ON_PY313 / DUAL_ACCEPTANCE_PENDING** | [PLAY48AC CI #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878), SHA `c9577d98`: Python3.13 verified **2 physically delivered bread** from genuine 3 claims over actual road at 48h; baseline0, true market food5 vs7, bakery10 completed, 12 copper unchanged. Python3.10 genuine 48h result pending |
| Exact Rules61 both-Python save safety and short property protections | **VERIFIED** | [#43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) code SHA `e3db72d8`: all short manifest, quoted offers, cargo and legacy **45/60 byte-identical rejection** jobs SUCCESS 3.10/3.13 |
| Exact Rules61 historical regression and true A/B | **PENDING FINAL CI** | [#43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485), no claim of new-head full passing or dual 48h result until those jobs finish |
| Historical previous Rules60 regression | **VERIFIED** | [#43037819648](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037819648) 1696/1696 each Python3.10 and3.13, does not certify Rules61 |
| Village 96h/endurance and independent 168h sustainability | **CONFIRMED NEGATIVE / RELEASE_NO_GO** | [#43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) genuine 96h: 13/13 starving and ZERO post72 deliveries/jobs/consumption/trade on BOTH arms; no verified 7-day recovery. Separate future approval required, never relabel this a passed recovery |
| Production `main` merge and save migration | **NO-GO** | No merge, no migration, no fabricated older-world compatibility. Stop transport scope after exact-head acceptance. No PLAY49 while phase-wide closure is unresolved |



## PLAY-48AC — authoritative manifest and explicit Rules61 gate (11 Nov 2026)

**Stage `PLAY48_OPEN / RELEASE_NO_GO`.** Source code remains Schema45 but is now **Rules61**, preventing silent changes to already persisted AA/AB Rules60 worlds. Neither old saves nor `main` were modified. Full provenance and QA: [PLAY48AC_RULES61_AUTHORITATIVE_CARGO_AND_RECOVERY.md](PLAY48AC_RULES61_AUTHORITATIVE_CARGO_AND_RECOVERY.md).

| Task | Status | Exact evidence / decision |
| --- | --- | --- |
| AB first 48h physical return | **VERIFIED DEFECT** | [#43037662900](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037662900), Python3.10 and3.13 both fail `pickup must use the local planned shipping lane`; the reducer was CORRECT to reject the controller's hard-coded index4 COPPER instead of signed FOOD. Do not suppress validator |
| AC one authoritative freight manifest | **IMPLEMENTED / SECURITY GREEN** | `choose_cargo_manifest` gives action+resource directly from same signed local transport lane. LivingWorld now uses it instead of hard-coded resource-by-stop index. [#43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878) Python3.10 &3.13 fast tests SUCCESS on exact code SHA `c9577d98` |
| AC real 13-NPC food movement for 48h | **VERIFICATION_PENDING** | Same [#43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878), true autonomous 24/48h A/B under Rules60; read `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD` after both versions complete before any positive outcome claim |
| Rules61 version boundary | **VERIFIED SAFE REJECTION** | [#43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) Python3.10/3.13 short security pass and authentic Rules60 SQLite-save rejected byte-identically by Rules61, zero migration |
| Rules61 full suite and actual 48h | **VERIFICATION_PENDING** | [#43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) runs complete historical suite and actual 13-NPC A/B on same Rules61 head under both Python versions; inspect job conclusions and individual logged evidence |
| Prior Rules60 full regression | **VERIFIED** | [#43037819648](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037819648) 1696/1696 PASSED on EACH Python3.10/3.13, after restoring accidental test partial wait to actual 59s |
| Huda wage/13NPC 96h | **VERIFIED NO-GO** | [#43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) both Python3.10/3.13 SUCCESS diagnostically; even with genuine 2 farm wages, **13/13 hunger100** and **0** deliveries/production/meals/sales after hour72 |
| New farm payroll replenishment | **NOT IMPLEMENTED** | Only after verified real physical bakery→farm bread receipt: require farm owned stock, fresh employer signed authorization, new real WATER delivery proof, no employee cargo consumption/double pay. Consider 1 grain:1 loaf fairness, bankruptcy, no rain and durable inventory |
| PLAY48 release | **RELEASE_NO_GO** | No 168h viable independent 13NPC test, no tested migration / production authorization, no `main` merge or PLAY49 |



## PLAY-48AA — lawful grain-for-bread freight physically returned to farm (2026-11-11)

**Stage PLAY48_OPEN / RELEASE_NO_GO; isolated Schema45/Rules60 experiment, no old save migration, no `main` modification.** [Current detailed provenance and results](PLAY48AA_INTEGRATION_SECURITY_AND_RECOVERY.md).

| ID | Classification / status | Verified evidence / next gate |
| --- | --- | --- |
| AA0 actual trusted farm-grain share configuration | CHAT_EXECUTABLE / VERIFIED | [CI 43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266) on tested source `4b4c8b66`: dual Python3.10/3.13 fast genesis and unauthorized cargo tests SUCCESS. No new grain, bread, money, paths or NPC knowledge; claim only earned after physical grain delivered |
| AA1 physical return/copper competition and customer property guards | CHAT_EXECUTABLE / VERIFIED_SECURITY_GATES | [CI 43034249899](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43034249899) Python3.10/3.13 **7/7 each**: reject already-quoted bakery loaves, one cargo per actual return lane, tampered claim counters, double delivery and forged first trip. These synthetic adversarial state tests are not themselves actual NPC journey evidence |
| AA2 true 13-NPC 48h food procurement | CHAT_EXECUTABLE / VERIFICATION_PENDING | [CI 43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266) two real 13-NPC worlds with same 3 starting loaves and 12 coins, bakery food and copper ledger, Huda freight, SQLite replay. Check result log `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD`; do not claim bakery-to-farm loaf physically delivered until tested |
| AA3 old 44/59 save protected under new 45/60 | CHAT_EXECUTABLE / VERIFIED_NEGATIVE | [CI 43033787068](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43033787068) both Python versions: genuine old saved world from frozen 44/59 source must reject in 45/60 **byte-identically**, no P0 migration |
| AA4 full 45/60 historical regression | CHAT_EXECUTABLE / VERIFICATION_PENDING | [CI 43033787068](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43033787068) source SHA `a9001058`; all `simulation/tests` historic tests, 23 current-world version assertion pins updated explicitly. Old 43/58 security fixture remains |
| AA5 real farm food→Huda earned wage and viable 7 days | BLOCKED_BY_DEPENDENCY / DESIGN_ONLY | A returned loaf belongs to FARM; its arrival does NOT silently replenish the pre-signed finite two wage units. Requires new signed employer food reservation, authentic water-service entitlement, adversarial drought/bankruptcy, real bakery production, legitimate market/customer quotes, and no cargo eating. Compare actual 1:1 barter impact and potentially 2 grain per loaf before any permanent rule |
| PLAY48 closure | RELEASE_NO_GO | No actual 168h work, deliveries and meals after hour72; no safe migration or approved merge. Remain within PLAY48, not PLAY49 |



## PLAY-48Y2 / Z — verified physical wage causality and real transport blocker (2026-11-11)

**Current branch** `experiment/play48y2-farm-wage-96h-and-workforce-20261111`; stage **PLAY48_OPEN / RELEASE_NO_GO**, experimental **Schema 44 / Rules 59**, original 43/58 saves **NOT MIGRATED**; no `main` merge. Detailed evidence: [PLAY48Y2_Z_VERIFIED_CAUSAL_RESULT.md](PLAY48Y2_Z_VERIFIED_CAUSAL_RESULT.md). Jobs classified before launch; don't infer success of 96h/full regression from shorter checks.

| ID / task | Classification / verification | Last evidence and next gate |
| --- | --- | --- |
| PLAY48Y genuine farm wages 48h | CHAT_EXECUTABLE / VERIFIED_CAUSAL_POSITIVE | [CI #43017271741](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741) SUCCESS on Python3.10/3.13 SHA `81cddebb`: 13 NPC and 12 copper unchanged, same true 3 opening bread (2 farm/1 market in BOTH arms). Huda physically earned and ate **two** genuine farm-water-delivery wages, hunger100→86 at day2, actual deliveries3→10, bakery batches9→10, village meals4→6, hunger100 residents5→4. Finite 2 wage ceiling, no bakery-to-farm replenishment |
| PLAY48V genuine Hana wages 96h | CHAT_EXECUTABLE / VERIFIED_NEGATIVE_ENDURANCE | [CI #43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657) SUCCESS on 3.10/3.13 at `37cd8fb5`: authentic 2 new Hana market-owned food wages, but BOTH A/B ar…32026 tokens truncated…CI before technical closure.

### PLAY-10 verified technical closure (2026-11-07)

**PLAY-10a–PLAY-10e CLOSED_TECHNICALLY** at exact code-and-test SHA
`1b4d60c301be4c158f4405dad52515c9092ac616`. [GitHub Actions run 42357107282](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42357107282)
concluded **SUCCESS**, with **1,339 passed on Python 3.10** and
**1,339 passed on Python 3.13**. All existing smoke, historic compatibility,
semantic parity and SQLite/replay gates also succeeded. This increases the
prior accepted suite of 1,316 tests by 23 parameterized PLAY-10 cases.

- A player-only `ask_food` executes one atomic `request_help` social exchange.
  The NPC's independent, prior-trust reaction determines whether its own
  direct or valid non-instantly relayed food belief is voluntarily shared.
- Only `unverified` hearsay is delivered into the player's durable memory;
  the narrator never receives remote resource totals, NPC hidden beliefs,
  goals, numerical trust or fabricated NPC speech.
- The opt-in disposable market fixture has exact finite square/woods food
  stocks (2 and 4) and two witnessed observations by physically present
  Basim/Omar; Salma has no inferred food memory. No resources are granted
  to Carlos or automatically consumed.
- Both real disposable CLIs implement `askfood <npc> <site>`, with
  explicit command-ID deduplication and restartable checkpoints.
- Tests cover voluntary refusal after a threat, several independent
  characters, co-location, knowledge boundaries, malformed input,
  failed/stale/duplicate operations, tampered provenance, SQLite
  snapshot/reopen and two-process CLI resume.

**Scope limitations:** Schema 33 / Rules 43 unchanged. No `main` merge,
canonical story mutation, extra player RPG powers or network authorization.
`03-A7c` and `03-A` remain **OPEN**; `P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain. The documentation-only closure
commit follows the tested SHA and is not itself the quoted code CI run.


## PLAY-11 — Physically local food survey and finite pickup (2026-11-07)

**Analysis before implementation:** PLAY-10 made food beliefs meaningful but
Carlos could not physically validate a claim or collect existing natural food.
The pre-existing NPC investigation/gathering event is NOT a player action.
PLAY-11 adds qualitative on-site survey and a player-bound one-unit pickup
of visible finite `wild_food` into explicitly initialized owner `food`.
The gateway groups a local player observation and pickup in one atomic
SQLite command; no hidden NPC inventory, hunger cure, XP, or food minting.
The new persisted event requires Schema **34** / Rules **44**. Independent of
03-A7c and production P0.

| Task | Scope and dependency | Route | State |
|---|---|---|---|
| PLAY-11a | Existing PLAY-10 green; present-only, qualitative local food check | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11b | One-unit PlayerFoodCollected reducer, active local player and source conservation | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11c | Opt-in fixture initializes player food=0, leaves older fixtures untouched | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11d | CLI checkfood/forage and revision-coherent narrator handoff | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11e | Many-NPC, anti-remote, anti-forgery, conservation, SQLite and two-CLI tests | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-11f | User guide and exact-SHA full dual-Python CI, compatibility version pins | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Limits:** visible, immediately pickable food only; timed searching/hunting
and player hunger relief are NOT implemented. No natural regeneration,
automatic player actions, remote location knowledge or RPG inventory.
No main merge or original story mutation. `03-A7c` / `03-A` OPEN;
`P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain. Do not close until exact
code SHA passes full Python 3.10 + 3.13 matrix.

### PLAY-11 verified technical closure (2026-11-07)

All six PLAY-11a–PLAY-11f tasks **CLOSED_TECHNICALLY** on exact final
code-and-test SHA `ed1385f8c18123498a534b101ad268331eac9fbb`.
[GitHub Actions run 42361210471](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42361210471)
finished **SUCCESS**, with **1,356 passed on Python 3.10** and **1,356 passed
on Python 3.13**. Compile, historical rules parity, prior saved-world
rejection, CLI, snapshot/reopen and integrity gates all passed.

The new `checkfood` action reveals only a qualitative on-site deposit;
`forage` groups an authorized player observation with exactly one
`PlayerFoodCollected` event, transferring one initialized natural food
unit from the player's physical location to its initialized own `food`
balance, atomically. There is no time cost, player hunger/health effect,
regrowth, XP or automatic RPG inventory mapping. Remote site stock, private
NPC resources and unknown balances remain inaccessible.

The source-conserving reducer is replay-safe. Dedicated acceptance tests
cover live Basim/Salma/Omar/Adel/Nora/Huda NPC coexistence, remote/false
actor/quantity rejection, missing deposits, depleted stock, travel time,
duplicate/stale commands, active-session/action capability, local observation
precondition, SQLite snapshots and both real CLIs across process restart.

Initial CI run 42360856576 on `3f19531d` **FAILED**: test expectations
still pinned to Schema 33 / Rules 43 and both CLI bootstraps referenced an
old fixture name. These were repaired across 18 files. No failing run was
used as closure evidence. The accepted tested SHA above uses **Schema 34 /
Rules 44**, and updates only *current* version assertions: all frozen
historical compatibility gates remain.

**Open:** `03-A7c`, parent `03-A`,
`P0_PRODUCTION_NOT_APPROVED` and
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER`. No `main` merge or canonical story
edits. The following documentation-only closure commit is distinct from
the exact tested code SHA; it is not claimed CI-verified by that run.


## PLAY-12 — Timed, source-competitive player forage (2026-11-07)

**Analysis before implementation:** PLAY-11's immediate `forage` does not let
the village live or its finite food supply change while Carlos works.
Reuse the existing trusted `ScheduledEventCreated` / `ScheduledEventFired`
mechanism with a reserved `__player_forage` payload. A verified 60-second
due signal physically checks remaining local food *at completion* and
transfers at most one unit; another real actor may take the last unit first.
No time/event writes happen in the background. This changes event semantics:
**Schema 34 unchanged, Rules 45** (old Rules 44 save rejected).
No independent production/medical phase is touched.

| Task | Dependency / result | Route | State |
|---|---|---|---|
| PLAY-12a | PLAY-11 green; start a genuine 60-second bounded scheduled activity | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-12b | Due-tick conservation and no-reward depletion; no instant pickup loophole | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-12c | Busy-player constraints; allow only waiting, reading own view and snapshot/resume | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-12d | Both real CLI workflows and coherent narrator-facing activity/results; 12a-c | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-12e | Independent NPC time, multiple player competition, forged schedules, stale IDs, SQLite replay and adversarial tests; 12a-d | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-12f | Guide, current-rules compatibility assertions, exact-code-SHA dual Python CI and technical close; 12e | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Safety constraints:** No automatic player decisions, real-time offline progress,
unknown or remote resources, instant harvest, medical effects or RPG inventory
conjuring. At the due moment, insufficient stock means **depleted**, no minted
reward. Only a real human-controlled actor present throughout may start;
`move`, `give`, `buy`, `talk`, `askfood`, `look` and another `forage`
are denied during the timed action; `wait` advances NPC autonomous activity.
A separately authorized player action cannot cancel or prematurely fire the
reserved schedule. `03-A7c` / `03-A` remain OPEN, P0_PRODUCTION_NOT_APPROVED,
EXTERNAL_REVIEW_DEFERRED_BY_OWNER. No `main` merge/story edits.

### PLAY-12 exact-SHA verified technical closure — 2026-11-07

**PLAY-12a–PLAY-12f CLOSED_TECHNICALLY**, against final source and test
SHA `fa935918ee7e9e5f8af60c1012c12f8826b04cae`. [GitHub Actions run 42366510974](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42366510974)
completed **SUCCESS**, **1,371 passed on Python 3.10** and **1,371 passed
on Python 3.13**, including extensive historical schema/rules parity, CLI
smoke, SQLite replay/snapshot and true two-process resume checks.

PLAY-12 changes `forage` into a genuine 60-simulated-second job. Player
action starts an atomic witnessed, source-bound, due-signal schedule; no
food is created or transferred on start. The world advances only by
explicit `wait`, while independent NPCs pursue their own actions.
At the signed due event, one unit is transferred from still-existing
wild_food at that site to the player's known food balance, or zero
units if the source was exhausted first. Concurrent player jobs resolve
by persisted due/order deterministically. The direct instant-pickup
event is disabled in Rules 45. Busy-player interactions, movement,
forged cancellation, missing source, backdated starts and remote
sources fail closed. Resuming an incomplete job does not advance
paused real-world time.

**Initial CI 42366073933 on 5e3f559b failed** (19 tests) because a strict
`dict` type check rejected the immutable `Mapping` payloads of real
DomainEvent objects. Corrected in the final SHA, plus a test-backed
prohibition of backdated starts that could shortcut the duration.
The failing run is not counted toward closure.

**Persistence:** Schema 34, Rules 45; rules44 saves are not silently
reinterpreted. No automatic NPC-to-player resource invention, hunger
healing, XP, equipment, canonical story edits or `main` merge.
`03-A7c` and `03-A` remain OPEN; `P0_PRODUCTION_NOT_APPROVED`
and `EXTERNAL_REVIEW_DEFERRED_BY_OWNER` remain unchanged.
This follow-up documentation-only closure commit is not the tested
code SHA above.


## PLAY-13 — Real player-owned meals, bounded meal history (2026-11-07)

**Pre-implementation analysis:** PLAY-12 yields genuinely owned `food`
from a finite 60-second forage. The market yields genuinely purchased
`bread`. No current player hunger, health restoration, magical abilities,
stamina recovery, XP or nutrition effects are modeled. To make eating a
concrete voluntary player action without inventing medical mechanics,
use a new `PlayerFoodEaten` event with existing trusted local
`consumption_authorized` capability. It decrements *exactly one owned*
food/bread and produces no other effects. The durable event log supports a
verified personal meal history. Event semantics change, so keep
**Schema 34 / Rules 46**; Rules 45 saves stay unsupported.

| Task | Dependency and deliverable | Route | Status |
|---|---|---|---|
| PLAY-13a | PLAY-12 green; player-only bounded one-unit eat from initialized owned food/bread | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-13b | Dedicated replay-safe event and trusted active-session consumption capability, no simulated medical effects | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-13c | Verified capped personal `meals` history and same-revision narrator handoff; no NPC privacy leak | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-13d | Real disposable and resumable CLI `eat <food|bread>` and `meals` | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-13e | NPC autonomy, missing stock, duplicated/stale/fraud requests, transit/busy, tampered replay, SQLite and two CLIs | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-13f | Guide and current-version compatibility pins, full exact-SHA Python 3.10/3.13 CI, technical close | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**Causal and scope constraints:** A meal is not a healing event or proof of
hunger relief. No NPC food/hunger changes, distant food access, timed player
auto-eating, free supply generation, player spellcasting, production
authorization, P0 approval, `main` merge or canonical story mutation.
No team may call these tasks closed until the full current-code SHA
is green for both Python versions. Open: `03-A7c`, `03-A`,
`P0_PRODUCTION_NOT_APPROVED`,
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER`.

### PLAY-13 verified technical closure — 2026-11-07

**PLAY-13a–PLAY-13f CLOSED_TECHNICALLY** on exact final code-and-test
SHA `24b2974599a213bada249d4781b64e55c5f96e39`. [GitHub Actions run 42373165522](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42373165522)
finished **SUCCESS**, with **1,410 passed on Python 3.10** and
**1,410 passed on Python 3.13**. Both matrices also passed historical
schema/rules compatibility, previous saved-world rejection, two-CLI
smoke tests, SQLite replay/snapshots, and real restartable world checks.

- A player can consciously use `eat food` for previously gathered food
  or `eat bread` for physically purchased bread. The dedicated
  `PlayerFoodEaten` event consumes exactly one initialized, owned
  unit without creating any substitute resources; no in-game time
  passes for this simplified immediate physical meal.
- The player-only gateway rejects unowned/unknown/empty food, nonfood
  resources, travel, simultaneous timed forage, NPC impersonation,
  unauthorized/off-session writes, forged/bad quantities and
  duplicate/stale request IDs.
- `meals` returns up to 20 event-sourced, integrity-verified
  personal receipts. The narrator handoff contains the five latest
  meal entries on the same world/revision as the other trusted player
  projections; it never reveals NPC private needs or ledgers.
- Existing NPC autonomy remains independent and untouched: there
  is no implicit player hunger change, HP, ST, MP, medical healing,
  XP, stat gain or NPC meal simulation change.
- Rules **46**, Schema **34**. Rules 45 saves are not silently opened
  under the new semantics. P0_PRODUCTION_NOT_APPROVED,
  EXTERNAL_REVIEW_DEFERRED_BY_OWNER and 03-A7c/03-A remain OPEN.
  Neither `main` nor the canonical Carlos story was modified.

**Closure mechanics:** This is a following **documentation-only**
commit; its SHA is distinct from the tested code-and-tests SHA above,
so the cited CI is not attributed to the documentation commit.


## PLAY-14 — Player sustenance evidence without unjustified hunger/energy (2026-11-07)

**Analysis before implementation:** NPC \`survival.py\` computes a trusted NPC
hunger/fatigue meter, while player \`rpg_state.py\` only has HP/ST/MP
with unknown-safe RPG values and no approved relationship to hunger,
calories or medical injuries. PLAY-13 deliberately consumes physical
owned food **without** changing a player hunger meter. Reusing NPC
metabolism on the player or equating ST with hunger would silently invent
a rule and could conflict with open injury 03-A7c/03-A. The safe playable
extension is an *evidence-only* \`needs\` panel, derived from verified meal
events, simulation time and initialized *player-owned* supplies. Unknown
remains unknown; no thresholds, hunger rates or injury effects are guessed.
No domain mutation -> **Schema 34 / Rules 46 unchanged**.

| Task | Deliverable | Classification | Status |
|---|---|---|---|
| PLAY-14a | Current NPC/player metabolism comparison and dependency boundary | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-14b | Verified last meal and elapsed simulated seconds, null when no event | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-14c | Player-only initialized edible balances with explicit unknowns and no NPC privacy leak | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-14d | Gateway \`needs\`, coherent narrator handoff and two real CLI routes | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-14e | NPC autonomy, unknowns, replay/snapshot, no wall-clock aging, no stat mutation and CLI tests | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-14f | Full exact-source-SHA Python 3.10/3.13 CI and technical closure | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-14g | Numeric hunger/fatigue, feeding rules, status penalties, injury integration | DECISION_REQUIRED / BLOCKED_BY_DEPENDENCY | OPEN |

**No gameplay hunger meter claimed.** 14g is a *different future task*
requiring an explicit game-design decision and assessment of incomplete
03-A7c/03-A. This batch adds no effect to HP/ST/MP, NPC behavior or RPG
progression. No production gate lifted; no \`main\` merge or canonical story
mutation. \`P0_PRODUCTION_NOT_APPROVED\` and
\`EXTERNAL_REVIEW_DEFERRED_BY_OWNER\` remain unchanged.


### PLAY-14 verified technical closure — 2026-11-07

PLAY-14a–PLAY-14f **CLOSED_TECHNICALLY** on exact code-and-tests
SHA `1cf0aadced5061667c4b9efe9f279882a1eccaef`.
[GitHub Actions run 42379710831](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42379710831)
completed **SUCCESS**, with **1,420 passed on Python 3.10** and
**1,420 passed on Python 3.13**, including historic Rules/Schema,
snapshot replay, independent NPC activities, real disposable and resumable
CLIs, and the new need-evidence tests.

A first test run at `74e851fb3d54d2099984663e195f277bbfc9213a`
failed two existing privacy assertions: a literal ban on the word
"hunger", and a literal ban on "bread" that now appeared solely as
**unknown player-owned bread** in the new evidence panel. No private
NPC production amounts or actual NPC hunger were exposed. Tests were
narrowly strengthened to assert `hunger == not_modeled` rather than
forbid naming the unknown, and reject leaked bakery recipe/output while
allowing an unknown player-owned bread label. The repaired source SHA
passed both full CI matrices.

The new read-only `needs` player command gives only physically owned
initialized food/bread (unknown remains null), latest *verified* player
meal receipt, and in-world elapsed seconds. It leaves player hunger,
physical energy and links to RPG stamina explicitly **unmodeled**.
It cannot silently advance offline time, mutate HP/ST/MP, create goods,
or query private NPC needs. Narrator handoff is version-coherent.

**No schema/rules change:** Schema 34 / Rules 46. The independent numeric
hunger and effects task **PLAY-14g remains OPEN, DECISION_REQUIRED /
BLOCKED_BY_DEPENDENCY**, until its game-design policy and injury
interaction are explicitly resolved; it is NOT technically closed.
03-A7c/03-A remain OPEN; P0_PRODUCTION_NOT_APPROVED and
EXTERNAL_REVIEW_DEFERRED_BY_OWNER remain. No main merge/story edit.
The present doc-only closure commit follows the exactly CI-tested code SHA.


## PLAY-15 — Opt-in independent NPC hunger and visible local meals (2026-11-07)

**Analysis before changes:** PLAY-14g (numeric player hunger, energy and
health effects) is explicitly DECISION_REQUIRED/BLOCKED and **not** a
prerequisite for existing tested NPC hunger/consumption functionality.
NPC `survival.py` and `consumption.py` already implement a deterministic
finite-food policy and food debit, but the default PLAY village deliberately
disables the feature. Reuse these proven rules in a **new, opt-in disposable
NPC-survival demo**. Basim and Nora start with exactly one initialized
owned `food` each and the other five NPCs start at known zero; hunger
starts at 80 in this *test-only* fixture, with no player health or hunger
effects. All NPC eating occurs only after explicit player `wait`, not
in offline wall-clock time. No new domain event, Schema 34 / Rules 46.

| Task | Deliverable | Route | State |
|---|---|---|---|
| PLAY-15a | Independent NPC hunger/policy reuse, keep PLAY-14g blocked and player unknowns | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-15b | Isolated seven-NPC opt-in finite food fixture; preserve standard fixture | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-15c | Trusted gateway enables NPC consumption/metabolism only on fixture marker | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-15d | Human at the scene sees only co-located eating events during explicit wait | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-15e | Both CLIs opt-in, resume must preserve scenario policy and reject mismatch without mutation | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-15f | NPC autonomy, privacy, gifts vs food, non-minting, replay/snapshot and CLI adversarial tests | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |
| PLAY-15g | Guide, whole-matrix exact-SHA Python 3.10 and 3.13 CI and technical closure | CHAT_EXECUTABLE | CLOSED_TECHNICALLY |

**No unauthorized nutritional claims:** NPCs only eat `food` already
initialized and owned; NPC `bread` is not converted to food without a
new recipe/policy. A meal witnessed during a wait projects **only** NPC ID,
observable eating activity, and logical time if Carlos was *not travelling*
and stood at the recorded consumption site throughout the wait.
Remote NPC meals, hidden hunger/food quantities, medical state and
NPC knowledge remain private. The player receives no automatic hunger
meter, HP/ST/MP changes, XP or any ability. Saved demo mode is bound
to exact bootstrap command ID and must be reaffirmed at resume;
no production migration or silent gameplay policy flip.

**Dependency gates:** `PLAY-14g` OPEN DECISION_REQUIRED,
`03-A7c` and parent `03-A` OPEN,
`P0_PRODUCTION_NOT_APPROVED`,
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER`. No main merge or canonical story
edits. Don't close this batch without full exact SHA CI green.


### PLAY-15 exact-SHA verified technical closure (2026-11-07)

**PLAY-15a–PLAY-15g CLOSED_TECHNICALLY** on the exact code-and-test
SHA `908e22f675641620d73f40f357b7264aa2997a33`. [GitHub Actions run 42381742262](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42381742262)
completed **SUCCESS** with **1,432 passed on Python 3.10** and
**1,432 passed on Python 3.13**, including historic schema/rules
compatibility, verified SQLite replay, snapshot/reopen, multiple
autonomous NPCs, resource integrity and both real CLIs.

- The regular disposable village stays unchanged and does NOT activate
  NPC hunger/consumption automatically.
- An explicit `--npc-survival-demo` option initializes only the special
  test world with seven real NPC agents and finite known food stock
  (one owned by Basim, one by Nora, five known zero). Existing, trusted
  NPC decision rules drive food consumption and baseline metabolism
  only during explicit player `wait`. Real autonomous work/rest can
  additionally increase NPC hunger.
- Player `wait` reveals only eating activity **actually co-located**
  with a stationary human during that wait, not remote NPC food,
  hunger levels, private knowledge or inventories. Player hunger
  remains `not_modeled`; HP/ST/MP are unchanged.
- Persistent CLI resume validates the exact opt-in fixture bootstrap
  command and rejects a mismatched `--npc-survival-demo` flag before
  allowing any gameplay or writing checkpoints.
- No new event type, Schema 34 / Rules 46 unchanged. No cannon story
  mutation, new player hunger, automatic player actions or P0 approval.

**First candidate** `7f41d0e3c5a5ffea1b331841eb3d638128540278`
had one test failure (1,431 passed, one failed on Python 3.13):
the test incorrectly expected Salma's hunger to be exactly 81 after
301s, ignoring the already-authorized additional hunger cost of NPC
work. The corrected expectation checks an honest lower bound instead
of asserting NPCs did no work. Both final SHA CI matrices passed.

**Open:** `PLAY-14g` (numerical *player* hunger and medical
effects) remains `DECISION_REQUIRED / BLOCKED_BY_DEPENDENCY`;
`03-A7c` and `03-A` OPEN;
`P0_PRODUCTION_NOT_APPROVED`;
`EXTERNAL_REVIEW_DEFERRED_BY_OWNER`.
The following documentation-only closure SHA is distinct from the
exact green code/test SHA above, and `main` is not merged.
