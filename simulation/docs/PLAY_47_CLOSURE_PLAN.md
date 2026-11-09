# PLAY-47 closure plan

**Status:** OPEN / RELEASE NO-GO. Work stays in PLAY-47 until its technical gates pass.

| Order | Work | Acceptance | Status |
| --- | --- | --- | --- |
| 1 | Integrate the verified PLAY-47 stack | Check targeted and full CI on the exact heads of PRs #53, #54 and #55 for Python 3.10 and 3.13. Advance the PLAY-47 branch only by verified fast-forwards. | In progress |
| 2 | Isolate the fourth-day delivery failure | Compare the same 13-resident world with and without a finite worker provision. Fix opening copper, total opening bread, roads, labor, weather and clock policy. Move existing bread into a named worker's ownership at genesis, debiting opening market stock by the same amount. Measure the effect on early market revenue as well as courier hunger, successful deliveries, harvesting, wages and actual meals. | Design checked against the supply reducer |
| 3 | Choose the smallest supported recovery | Keep provisions as an experimental initial allocation. Consider a local fee from actual market proceeds only if the comparison shows food access is the bottleneck and workers can buy food on their routes. A courier fee needs a separate ownership contract before implementation because the current copper slot is used for reserved cash consignments. If the limiting factor is physical capacity, record the observed deficit and stop the repair branch at that evidence. | Depends on step 2 |
| 4 | Verify endurance and adverse cases | Use the same 72-hour and 96-hour checkpoints. A recovery claim requires a real post-stall delivery and subsequent production or purchase attributable to it. Run seven days where feasible with recorded resource sources, keeping the unrecovered control. Cover drought, depleted treasury, missing road, unavailable seller, duplicate payment, attempted use of consigned cargo, old-save rejection, default-off parity, SQLite reopen/replay and clock partition equivalence. | Pending |
| 5 | Decide and record technical closure | Targeted and full CI must pass on the final exact SHA on both Python versions. Record verified outcomes, any capacity limits and review status in the phase report and work queue. The established criteria allow documented finite-resource failure as an experimental outcome. An unexplained divergence or violated accounting invariant blocks closure. | Pending |

## First experiment

Run the existing 13-resident case as the control. In the comparison reserve one
of the three opening loaves as Hana's personal provision at genesis, leaving
two loaves available for the initial market. Both runs start with twelve
copper and three total loaves. The causal question is whether the allocation
keeps the eastern route operational longer and what it costs in initial sales,
farm receipts and wages. Compare through hour 96. A later variant can change
the recipient while holding quantities constant, if the first comparison is
ambiguous. No free stock or new currency enters either world.

The day-four evidence rules out additional rain alone as a recovery in this
fixture. It shows unused water, no additional deliveries and five unsold
loaves. It does not establish that compensation is sufficient. The supply
reducer also requires a zero courier copper balance when loading cash and an
exact one-coin balance when delivering it. Funding wages into that same balance
would conflict with the existing custody rule. The first experiment therefore
uses separately owned opening food and the existing consumption protections.

## First experiment result

The locally measured provision case moved one opening loaf from market stock
to Hana. She ate it and reached hunger 53 at hour 24, then reached hunger 100
by hour 48. By hour 96 her route still had 25 completed deliveries, the same
as the unprovisioned control. No delivery was added during day four. Initial
food revenue fell from six copper to four because only two loaves were for
sale at the opening tick. The test case preserves the opening total of three
loaves and twelve copper and reconciles the physical ledgers daily.

The single opening provision delayed hunger without extending the route.
A fee paid into the courier's current copper slot would still conflict with
consignment custody. The evidence leaves durable worker access to food as an
unresolved capacity limit. Keep the bounded trial as a negative control and
avoid treating a one-time provision as recurring compensation.

## Market custody regression

An idle courier at the market holding one reserved copper previously received
a one-copper bread purchase intent. The market reducer also allowed the
transfer in isolation, although it would invalidate supply custody at the
world boundary. Food purchase planning now subtracts reserved payment, and
the market reducer checks available units on both outgoing sides before any
transfer. The reproduced state uses a real supply pickup and a local posted
loaf. The attempt leaves the market, wallet and cargo ledgers unchanged.
This hardening does not add courier wages or alter the currency schema.
