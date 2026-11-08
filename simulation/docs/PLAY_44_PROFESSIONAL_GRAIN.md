# PLAY-44 — Autonomous professional grain procurement (opt-in)

Status: candidate under test. Branch based on PLAY-43 exact full-green
\`fa0ee2671831749fdfd36aaaf4e381580e3fe3de\`.

Batch contains: (1) local finite farmer grain quote; (2) actual baker decision to
explore only surveyed local roads when workshop is missing input; (3) buy only
a physically co-located affordable quoted unit with baker's existing copper;
(4) return along individually learned roads and deposit owned grain into
the workshop with the protected PLAY-43 reducer; (5) let the ordinary
production/bread sale/funded wage loop run, with repeat visits only after
new earned wages and *remembered own* earlier grain purchase.

Flag: \`professional_procurement_enabled=False\` by default, requires
economic+agriculture+economy-only+routines+navigation and forbids running
hunger shopping concurrently until behavior interaction is tested.
No new event type, schema field, event interpretation, or SQLite command flag
was introduced: Schema 41 / Rules 56. Every autonomous outcome uses existing
registered/replayable MarketOfferPosted, MarketTradeExecuted,
WorkshopMaterialDeposited, ScheduledEventCreated, NPCTravelStarted,
NPCNavigationSurveyed and ProductionStarted reducers. New rules cannot be
activated in saved sessions except by an explicit opt-in engine setting.

Seller may see own local inventory only. Buyer sees the actual quoted
seller only after arriving. The buyer's outbound exploration does not
inspect remote goods, prices, registered faraway stalls or hidden labor
availability. Repeat supplier visits derive solely from the buyer's own
earlier grain-purchase receipt plus a new paid job receipt. An unfunded or
unsuccessful trip returns physically, never creates a unit or coin and
does not cause fruitless repeated market oscillation without new wages.

Failure cases: no known road, no local seller, no quote, no wallet funds,
busy producer, full output stock, uninitialized input/tool, and no new wages
must all stop/fail without fabrication. Demonstrate two physical work
cycles with finite farm grain and real customers; not indefinite autonomy.
All author-tested CI evidence must be recorded for the exact candidate.
No external review or production P0 release implied.
