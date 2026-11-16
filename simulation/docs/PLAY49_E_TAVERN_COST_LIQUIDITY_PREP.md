# PLAY-49-E — real cooked-tavern economic viability audit (PREPARATION ONLY)

Date: 2026-11-16. Parent PR140 SHA
0215b166d985018c537ae8aac0df3929d761d054.
No core engine, existing PLAY48 or previous PLAY49 branches edited.

## Audited alternatives
1. Existing fixed 3-copper menu: cook purchases actually sourced fruit
   and cheese from Huda for **2 + 3 = 5** owned copper. Real Salma meal
   sale brings in **3** venue copper, one original agreed cook wage
   transfers **1** to cook. Business liquidity (tavern + financing
   cook) is **5 opening -> 3 closing: loss 2**, even though the plate
   genuinely reduced hunger. A real meal is not proof of viable profit.

2. Alternative **explicit genuine 6-copper quote**, exactly covering
   ingredients 5 + one paid wage 1, using the same earlier finite
   orchard/cheese production receipts. Salma has only **5** and
   cannot buy it. Huda legitimately holds **12** after her trade
   and is already physically present at the tavern, so she can pay
   6 from her own money and eat. The already completed cook gets
   one signed, actually funded wage. After the sale: venue **5**,
   cook personally **1**, vs opening venue0 + cook5 = **+1 net**.
   All known copper is conserved, no implicit extra food.

3. Still **NOT sustained**: cook began with 5 and ends with 1.
   Venue treasury's 5 belongs to the site, NOT automatically to
   the cook. The orchard fruit and the dairy milk are physically
   exhausted, and a second plate is rejected. No assumption of
   automatic borrowing, refill, magical cash circulation or
   independent customer funds.

## Gates
- One-tick and split-time equivalent economic receipts; no remote
  purchases, including real Salma buyer with insufficient 5 copper.
- Genuine source→trade→deposit→timed cooking→trade→single wage→
  actual NPCFoodConsumed for Huda with a verified 20→0 hunger effect.
- Exact SQLite replay, snapshot, integrity and no duplicate meal.
- Python 3.10 and 3.13 focused CI on exact branch HEAD.
- All modifications are new test, CI and documentation files only.

**No autonomous merchant AI, renewable milk/fruit, 96/168h viability,
completed PLAY49, merge or release authorization.** The real 13 NPC
PLAY48 acceptance remains blocked. Stop before claiming sustainability.
