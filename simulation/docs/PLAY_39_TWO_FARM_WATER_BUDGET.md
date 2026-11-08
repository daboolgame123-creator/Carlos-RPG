# PLAY-39 — water-ledger and food-output experiment across two real-day fields

**Objective:** Test what remains broken **after** PLAY-38 physically opened a second farm and courier. This phase does **not** grant food, bypass NPC hunger or declare long-term sustainability.

## One genuinely controlled experiment

Two independent SQLite worlds, nine named autonomous NPCs, two real physical farms, two real couriers, a bakery and a market. Existing base farm plot grows one 24-hour crop producing three grain; second farm is explicitly configured at genesis with a separate real 24-hour plot and an illustrative yield of seven grain per seed lot. **Yield seven is a deliberately labelled test-world agronomic assumption, not a globally adopted medieval crop standard or free food.** Both plots consume one physical unit of water per growth; seed lots return only on documented maturation, and every baked loaf requires a local grain input and actual baker job. Starting market stock is three physical loaves. Total cash stays twelve copper; some NPCs may be unable to afford food, and nobody receives magical wages.

Both worlds run **full NPC autonomy**, not the economy-only mode, with the same already-supported time-zero 3600-second hunger period and 20% activity hunger policy. No code path changes worker thresholds or NPC choices. The **sole later difference** is receipt of two finite, explicitly authorized rain water units at logical day one and day two in the wet world; the dry control receives no rain at all. The water source is a real configured well of capacity eight, with each receipt having a unique measured-observation ID. This is **a synthetic attested-rain counterfactual**; it is not a claim of real observed weather or an autonomous rainfall oracle.

At each of t=0, 3600, 86400, 90000, 172800, 259200 seconds, and at intermediate 6-hour material transitions, require an exact accounting identity: **initial 2 water + sum of recorded rain = water at all physical sites/couriers + all growth cycles started**. Separately reconcile seed lots, yield-dependent crop readiness, completed/ongoing harvest jobs, stored grain, ongoing bake jobs, every owner-owned loaf and actual consumed meals, plus conserved twelve copper. All checkpoints compare genesis replay to stored SQLite and snapshots.

## Why this matters

A nine-NPC world requires **at least nine loaves per day at the already-supported slower metabolism**, disregarding exertion, ownership and startup reserves. Two fields with ideal 3+7 daily yields could theoretically supply ten loaves per day **if** adequate water and real labor actually sustain the crop cycle. Two actual courier contracts have sufficient mathematical throughput in this configuration, but physical transportation, fatigue, hunger, job shifts and inaccessible marketplace money may prevent it. **Numerical upper bound is not actual nutrition**; print and compare named stages and the number of people in hunger 100, and never declare success without every meal and all daily physical budgets.

The experiment is deliberately scoped to 72 hours. Failure in the dry world is normal and must not be fixed by inventing rain; failure in the wet world triggers a distinct analysis of work schedules, affordability and contracts. Subsequent phases need real funded provisions/wages, lawful physical local deliveries and more than three days of credible stable trajectories.

**Quality:** Python 3.10 and 3.13 targeted CI, exact-SHA full historical regression, independent adversarial duplicate/unauthorized precipitation tests, no `main` changes, no hidden actor knowledge, no claims of independent external review or P0 release clearance. Store is schema 40/rules 53.
