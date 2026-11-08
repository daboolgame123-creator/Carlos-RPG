# PLAY-29 — Food capacity and metabolism calibration (pre-implementation)

**Status:** PHYSICAL_CAPACITY_ANALYSIS_ONLY. No modifications to engine,
world versions, food inventory, or historical state. Branch
`design/play29-food-capacity-20261108`.

## Root cause measured from real source and PLAY-28B experiments

- Current `survival.py`: 1 hunger point per **300 logical seconds**.
- Current `consumption.py`: one owned food unit relieves **25 hunger points**.
- Seven people therefore accumulate **2016 potential hunger points/day**
  before saturation, equivalent to an idealized long-run **80.64 food units/day**
  if hunger is to remain stable; individual meal granularity matters.
- Current test village: one finite field matures **1 crop/day** given real
  seedling and finite water. The harvest and bakery convert one grain into
  one food. Even at its optimistic upper bound, **1 food/day** cannot
  maintain seven people at the currently configured metabolic rate.
- The 72h rain-vs-drought experiment measured **1 vs 2 matured crops**,
  yet hunger hit 100 in both; improving water alone cannot resolve this.

These figures are a **structural upper-bound diagnosis**, not a claim that
the engine actually produces 81 food items each day or serves fractional
rations. Hunger saturates at 100 and some NPCs stop working.

## Engineering next slices (separate acceptance gates)

1. **Metabolism realism:** create controlled alternatives for hunger clock
   (e.g. 300 vs 3600 sec per point); do not change the historical constant
   silently. Any approved change must be versioned and replay-safe, with
   no decrease of hunger without consuming existing food.
2. **Bounded acreage:** each newly available field must occupy explicit
   land, require genuine seed/tool/labor, water shipped by the courier and
   mature through actual clock time. Avoid unlimited simultaneous crops
   and instant harvest.
3. **Physical yields:** permit a larger harvest only with documented
   acreage, fertility and time constraints. A yield is biological growth,
   not a generic resource-credit command.
4. **Access/distribution:** measure whether bread reaches the actual
   consumers through known markets and coin balances; mass baking at
   an inaccessible site is not nutritional survival.
5. **Long-run A/B:** seven named NPCs; drought and recorded rainfall,
   food scarcity and finite provisions. Test 3/7/14 logical days, full
   metabolism and AI on, checkpoint/save/replay, every physical ledger.
6. **Measure:** crop output/day, meals/day, stock levels, starving NPCs,
   wages/copper flow, walking time, labor time, land/water limits,
   and whether results stabilize after initial provisions are exhausted.

**Safety and scope:** No spell-based harvests, free food, NPC teleport,
unlimited well capacity, or changes to main. Work on independent branches;
do not present an optimistic theoretical capacity as actual village output.
