# PLAY-45 — Multiple real professions and material-backed local shops (opt-in)

Status: **IMPLEMENTATION CANDIDATE — NOT CLOSED**. Depends on technically closed PLAY-44 at exact SHA `38062e5308bde90bc1b016f0aeaf571aebd8305a` (full CI run 42532536124: 1,694 green on both Python 3.10 and 3.13). Stack on that branch; no `main` merge.

## Root-cause scope

PLAY-44 proves one baker who owns paid grain can return and bake, but an independent economy needs multiple genuinely occupied workplaces, real material inputs, products consumed as other workers' inputs, market receipts, finite existing wallets, worker shifts and personally learned physical routes.

**This batch deliberately does NOT add compound recipes, smelting fuel, timber regeneration, dairy perishability, tavern staffing or arbitrary buyer preferences.** The existing production model accepts *one consumable input and one non-consumed physical tool per recipe*. Adding a second simultaneous consumable material changes persisted recipe/job format and demands its own save-compatibility phase; it must not be hidden as a fictitious extra tool.

## Five linked tasks

1. Add a separate `multi_professional_markets_enabled=False` opt-in: preserve PLAY-44 grain behavior and all legacy modes unchanged; require economy-only, agriculture, navigation and routines; disallow simultaneous grain-profession and hungry-shopper route planners.
2. Generalize local material sales to two finite **primary suppliers**: woodcutter-owned `wood` and miner-owned `iron_ore` using actual staffed local markets. Producers may post only their own recipe's real finished output, never a remote workshop input or busy equipment.
3. Material-dependent professionals decide to explore **only personally surveyed roads**, buy **only on-site** with real wallet coins, carry owned stock back physically, and deposit into the correct workshop via the preexisting trusted reducer. Failed trips should not make perpetual oscillations or invent suppliers.
4. Validate an actual interconnected chain: wood -> carpenter -> `plank` -> builder's documented `frame`, and iron ore -> smith -> `iron_fitting` -> repairer's `fixed_gear`. Each output is produced by a real scheduled job and the intermediate output is actually purchased and consumed by the next workshop. Workshop sale income is the only eligible source of configured wages.
5. Adversarial tests: wrong/absent seller, insufficient/unknown wallet, no known road, emptied stock, no duplicate cargo or fabricated copper, local temporal ordering, SQLite genesis replay/snapshot, default-off parity and two-Python-version full CI.

## Economic correctness

Finite starting stock is an explicitly declared **disposable test-world initialization**, NOT autonomous resource extraction. The 6-copper test pool is initialized once and remains 6. No item or copper created by NPC intentions: production changes input->output under an actual recipe, shop transfers preserve amounts and buyers cannot see remote quotations or jump between places.

Even if this entire batch passes, it demonstrates only a finite multi-profession economic chain, **not long-term self-sufficiency**. The next distinct phase would add authenticated multi-input recipes, tool repair, renewable materials and harder insolvency/competition scenarios, then later perishability and taverns.

## Release gate

Candidate branch + PR remain draft until targeted checks and full historical regression pass on the final same code SHA for Python 3.10 and 3.13. Report external review and P0 separately; do not conflate technical closure with production approval.
