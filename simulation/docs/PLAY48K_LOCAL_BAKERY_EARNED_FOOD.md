# PLAY-48K — Remove the real courier-wage collection-site deadlock

Status **experimental**, `PLAY48_OPEN / RELEASE_NO_GO`. Schema43 / Rules58 baseline; version policy must be reconsidered before any release (new allowed payer sites).

**Observed:** 96h I test proved PAYROLL alone paid both regular production workers but failed to revive the village at hour 72: 12/13 NPC at max hunger, 0 additional jobs/sales/meals between 72-96h. H3/J2 early market food wages paid Hana at market but Huda wasn't paid even after 3 real deliveries; at the same time Huda cannot buy food with empty personal cash while site treasuries own existing money. The site of pay and physically reachable workplace may therefore be the causal blockade.

**Distinct credible intervention:** At initial trusted world genesis only, the original three market loaves are assigned **two to market and one to bakery**; total 3 unchanged. The actual employer in the bakery signs a pre-funded 1-loaf in-kind contract for Huda, debiting the bakery's true owned bread. The market still signs a 1-loaf contract for Hana, leaving 1 unreserved market loaf. Both A/B arms share this EXACT genesis, same 13 NPC/12 copper, workers' jobs and actual streets. In the treatment only, a Huda who **actually transports grain to the bakery** receives a bakery escrow loaf immediately *after her own exact same-command physical grain-delivery receipt*; without completed service she is never paid. The baseline keeps that same bakery wage unpaid until eligible payment happens (which requires explicit new opt-in).

**Trust boundaries:** The store rejects forged early bakery food wages without immediate same-worker/time GRAIN delivery; the event reducer checks actual circuit index 2, physical bakery location, idle worker, correct contract, site-owned escrow and unique service count. No teleport, free labor, hidden site stock, special hunger immunity, or minted coin.

**Gates:** negative forgery test and both 3.10/3.13 genuine 12h runs, then a separate 96h 13 NPC A/B with authentic real water, food+escrow conservation, 12-coin ledger, real income/production/meal counters and post-72h changes. If the whole economy still freezes despite courier early bread, this is a real negative result. Do not close PLAY-48 based only on a first earned meal. No PR merge, no PLAY49.

The user explicitly wants the village's independent causal economy, not happy-result scripted NPC actions.
