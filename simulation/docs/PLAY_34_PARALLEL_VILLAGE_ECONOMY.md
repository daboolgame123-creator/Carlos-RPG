# PLAY-34 — two independent NPC villages, 24-hour economic audit

**Scope:** Experiment, not gameplay feature, financial forecast, or proof of sustainability.

The scenario runs **two fully separate disposable SQLite worlds**, each holding seven autonomous NPCs across the same physical road/farm/bakery/market system, for a simulated day. There is **no connection or trade between the two villages**. Carlos gives no NPC instructions and no runtime stock subsidies.

Control A and B use equal starting food (3 physically stored market loaves), water (2), seed (1), crop yield (3), initial hunger, and **12 copper** in total. In A eight spare copper remain with Carlos; in B those *same* eight opening copper are split between Omar and Layla. This is a **fixed bootstrap counterfactual**, not an autonomous redistribution/wage policy.

At simulated t=300, 3600, 21600, 86400, record each NPC's hunger, real market buyers, meals, cash by owner, bakery/field/courier state. At every checkpoint, audit physical conservation, assert no negative quantities, compare SQLite live state to full genesis replay and verify snapshot. These private diagnostic metrics never enter the player's knowledge or narrative.

The first 300 seconds should reproduce verified PLAY-30C observations: 1 vs 3 trades, same three finite loaves and aggregate money. **Long-day outcomes must be measured**, never assumed. Failure to feed NPCs does not mean the test is invalid or a surviving village is established.

**Gates:** Python 3.10/3.13 targeted workflow, historical regression on final exact SHA. Open: external independent review, 03-A, PLAY-14g and production P0. No changes to `main` or canonical story.

This stage establishes measurable economic exclusion and hunger under independent local conditions. Follow-up economy design should address *earned, finite, recorded wages and genuinely observed market access*, not scripted NPC prosperity or instant global trade.
