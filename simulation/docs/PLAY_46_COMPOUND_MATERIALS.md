# PLAY-46 — Real compound materials with atomic workshop production

**Status:** implementation candidate, open until all acceptance gates pass. Base: PLAY-45 `a6c20e3edfbe85cc68819cd4fadd909472b21fd5` (1,694 green on Python 3.10 and 3.13).

## Persistence and legality contract

- Schema **42**, Rules **57** because persisted recipes/jobs now admit a new compound structure. The original v41/56 SQLite file is intentionally rejected before replay; no silent upgrade or reinterpretation. A new and separate migration process would require approval before changing a preserved world.
- Legacy recipe retains `input_resource` and `input_amount`, and its job retains the exact scalar `input_before` and `input_after` receipt keys.
- Compound recipe instead requires an `inputs` list of 2–4 **distinct, initialized, local** `{resource,amount}` objects; each amount is an integer 1–1,000. Neither legacy input fields nor a mixed form is accepted.
- The product and unconsumed tool are distinct from every input, and no inputs, tools or outputs may use money (`coin_copper`) or reserved pseudo-resources. No resource's absent balance is inferred to be zero.
- Before starting, the authoritative reducer validates all locally owned stocks, output capacity, available physical tool, worker profession/presence and running action/job collisions. Only if **all** pass are all inputs consumed in a single event. Rejected events cannot commit any partial debit.
- Compound production jobs store `input_before_by_resource` and `input_after_by_resource`, requiring exactly the configured resource keys and precise per-resource subtraction. Completion creates the actual product only at the trusted due tick. Wages are one-time and funded only from the workshop's real copper.
- The same trusted workshop-deposit event permits the worker to deliver any legitimate recipe input locally but never reserved courier freight.

## Real-world acceptance proof (finite disposable village)

A test-world initializes **4 copper** at t=0, one miner's ore, and one charcoal producer's fuel. A smith makes **four real physical route legs**, purchases ore and charcoal at the staffed local stalls with personal copper, carries them home, deposits both, schedules the two-input `iron_fitting` job, sells the finished fitting to a real repairer and receives one funded wage from that sale. The world ends with exactly four copper; neither ore nor coal is produced from nothing.

**Important distinction:** the 4-copper physical integration explicitly drives trusted movement/market APIs; it demonstrates physical transaction integrity, not autonomous planning by itself.

Separate opt-in autonomous tests (`test_smith_autonomously_buys_both_distinct_inputs_on_roads_and_smelts`, `test_all_three_trades_both_professions_act_without_manual_commands`) verify a smith using personally surveyed roads and its own contract/market receipts to buy ore and charcoal, deposit them, and smelt without scripted travel, buy, or production commands. A second autonomous profession buys the finished fitting and repairs gear. That six-copper scenario produces **3 real trades, 2 completed jobs, 1 sale-funded wage, and conserved 6 copper**. Decision intent is derived from durable job/trade/travel receipts rather than an explicit new stored goal field. Local seller presence, failure of absent suppliers, replay consistency, and partitioned-vs-lumped world time have dedicated tests. Production consumes both inputs atomically; the two market purchases are separate real transactions.

## Remaining closure conditions

- Reconfirm the existing opt-in autonomous procurement, seller-unavailable behavior, and time-partition invariance on the exact final commit under both supported Python versions.
- Verify test-world snapshot/replay and the predecessor's genuine v41/56 SQLite file without byte mutation.
- Full historical regressions green for Python 3.10 and 3.13 on the final exact code SHA.
- PR remains **Draft**, no main merge, P0 and independent review still separately open.

No claim of long-term economy sustainability or release readiness follows from these limited scenario fixtures.
