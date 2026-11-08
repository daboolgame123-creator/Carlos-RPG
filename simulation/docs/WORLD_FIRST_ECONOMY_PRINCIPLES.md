# Carlos world-first economy: binding design rules

Decision reaffirmed 2026-11-08. This is an architectural principle, **not**
a claim that all listed jobs and shops are implemented.

## World before player

The village is not built around Carlos's presence. NPCs have their own
limited information, needs, labor shifts, physical workplaces, stock,
money, trade, and routes. The player may observe or participate but does not
spawn the economy, trigger distant trade, or grant free salaries.

## Physical invariants

1. **Every unit has provenance.** Raw materials originate from a bounded
   test-world initialization, a recorded harvest, or a documented conversion.
   Workshops consume inputs and tools cannot work in two places at once.
2. **Copper is a conserved stock.** Finite opening copper can change owners
   through recorded sale, delivery, wages or later documented transactions;
   it cannot be minted per daily tick. Failure of liquidity is a legitimate
   outcome. A worker is paid only by a local funded employer.
3. **Ownership is not consumption.** A purchase debits seller stock and buyer
   copper and credits buyer stock and seller copper. Only a subsequent real
   consumption event relieves hunger. Shop listings are not infinite stock.
4. **Local knowledge, physical travel.** A villager uses only personally
   surveyed roads and takes actual route duration; an unknown shop, unseen
   warehouse or remote quote cannot guide a privileged path. Return travel
   uses the same known roads. Travel, active production and eating cannot
   overlap in physically impossible ways.
5. **Agents act for reasons, not animation.** Hunger, sufficient wallet,
   work, personal experience, scarcity and safety motivate choices. Empty
   stores, unaffordable items, impassable/unlearned routes and lack of cash
   may block trades. Never fake success to keep the scene lively.
6. **Existing worlds stay safe.** New autonomous behavior starts as an opt-in
   rule, is tested against default-OFF replay and historical SQLite, and is
   not merged merely because a targeted green check passed.

## Incremental economic topology

- PLAY-41: one-time funded wages paid from actual market income carried along
  courier routes. Completed, full historical suite green on both versions.
- PLAY-42: opt-in hungry shopper explores locally known roads and physically
  visits an actual staffed market. A funded affordable loaf can be bought,
  eaten, and followed by a known-road work return. An unfunded or too-small
  wallet does not produce a trade. **This phase is under verification.**
- Future extensions, subject to separately tested contracts:
  - Carpenter: wood/tools -> doors, furniture, wagon repairs; real buyers.
  - Blacksmith: ore/charcoal/tools -> nails, implements, repairs.
  - Produce/dairy seller: finite fruit/cheese supply with perishability.
  - Tavern: meals, firewood, lodging and real employee payroll.
  - Multiple competing shops, independent ownership, delivery contracts,
    price discovery, shortage, insolvency and inter-village trade.

**Do not add every store at once.** For each, first prove the resource
origin, recipe, owner ledger, NPC reasoning, transport, accounting, and
conservation under normal, insufficient-funds, shortage and adversarial
tests. The aim is self-sustaining, emergent NPC society, not a scripted
sequence of visible transactions.

## PLAY-42 verified acceptance gates

- All travel uses real routes; in-flight NPC remains at origin until due.
- One- and two-copper wages are distinct time-zero contracts and both
  require physical site cash at settlement.
- An unaffordable quote remains unaffordable; a valid quote/stock enables
  a locally recorded purchase and an independently recorded meal.
- After a real paid meal, the NPC uses their learned physical road graph
  and existing shift routine to return to a reachable workplace.
- Total opening copper remains 12 in the two-field disposable test world;
  persistent snapshots must exactly match event replay.
- Python 3.10/3.13 targeted and full regressions, compatibility gates and
  a reviewed PR are required before technical release closure.
