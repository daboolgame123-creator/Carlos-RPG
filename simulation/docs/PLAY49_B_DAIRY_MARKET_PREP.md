# PLAY49-B — finite dairy market preparatory experiment only

Date: 2026-11-16. Parent PLAY49-A SHA dc70f141f12a313b01bfa42caa6d0e125df84046.
OpenCode owns PLAY48; this branch is tests/documentation only.

Three physically distinct, staffed markets: bakery, orchard fruit, dairy cheese.
The dairy receives a declared, FINITE t=0 inventory of 2 owned milk units and
one press. An actual trained cheesemaker uses 180 simulation seconds to turn
2 milk into 1 cheese, earning precisely 1 real employer copper on completed
work. Separate on-site seller receives real customer copper into the dairy
owner's till. Real buyer must walk bakery→orchard (50s)→dairy (70s), and may
inspect only local offers. Existing bakery and orchard continue to work.

All new opening milk/copper are declared fixture genesis stock; no production
of new milk, unseen livestock, refill, ongoing nutrition, spoilage, tavern,
or sustained autonomous village economy are claimed. Neither fruit nor
cheese automatically constitutes edible legacy 'food' and neither is
credited as a meal. One finite batch only is a deliberate test boundary.

Tests reject remote and mid-transit purchases, forged shop owner,
unproduced/oversold cheese, unauthorized/overpaid/duplicate worker wages,
and second batch after consuming all initial milk. Replays/checkpoints,
SQLite integrity, conservation of copper after opening are verified.

STATUS: PLAY49_PREPARATION_ONLY / DRAFT_NO_MERGE; PLAY48_OPEN /
RELEASE_NO_GO. No main or core engine edits, no phase closure.
