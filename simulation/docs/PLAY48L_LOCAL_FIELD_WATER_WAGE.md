# PLAY-48L — True early worker pay at the reachable FARM, not the 1-day bakery

**Status: PROTOTYPE / RELEASE_NO_GO**; same genuine 13 NPCs / 12 copper / original 3 opening loaves. No automatic salary creation.

The preceding [PLAY48-K](../scenarios/test_village/test_play48k_local_bakery_courier_wage.py) proved a necessary negative: Huda delivers WATER to the field several times in the first 12h, but first-season **GRAIN does not physically exist yet**, so a salary only for grain delivered at bakery cannot be paid during the early hunger window. A green anti-forgery test (rejecting fake receipts) is insufficient; the worker still has an actual early job but no early income.

**Better genuine policy**: At trusted genesis, ONE of exactly three original market loaves is **initially owned by the actual field** (2 market + 1 field, instead of 3 market + 0 field). The real field owner escrows this single pre-existing loaf to compensate courier Huda for an actual WELL→FIELD *WATER DELIVERY*, with exact same-command event proof and the physical Huda present at the correct planned first stop. Another pre-existing market loaf is escrowed for courier Hana's market delivery. One saleable market loaf remains. Original cash/employer 2-copper wages unchanged.

Two 13-NPC worlds get identical opening ownership and precisely two separate signed contracts, with **only the authenticated early farm food payout enabled** in one arm. Every paid unit decreases escrow and appears in the legitimate recipient's personal inventory; it must be eaten according to standard hunger rules. Check server event log, fraud rejections, food and water + escrow conservation, owner by owner 12-copper total; then 96h 72→96 activity and 7day feasibility. If even this first legitimate courier meal fails to carry physical and financial circulation through 72h, PLAY48 cannot close and requires *food supply capacity + reachability*, not more salary variants.

Any hypothetical stronger village food infrastructure belongs to a later **separately justified genuine agricultural-capacity experiment**, with actual fields, workers, routes and water and without importing free inventory during runtime.
