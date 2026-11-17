# PLAY49-I — autonomous local venue ingredient procurement (isolated, opt-in)

Date: 2026-11-17. Parent PLAY49-H `0ec0af5126fdd9c007cc5939c8773fdd6293ff37`.
Status: **DRAFT / PLAY49_PREPARATION_ONLY / PLAY48_OPEN / RELEASE_NO_GO**.

## What this adds

The genuine two-meal PLAY49-G economic case had to tell the tavern keeper to spend the tavern's wallet. This trial introduces a pure, deterministic **local venue purchase intent** and passes it through the existing market event reducer during `LivingWorldEngine.advance`, but ONLY if the new `site_procurement_enabled=True` flag is expressly enabled along with `economic_enabled=True`. The default is `False`.

One locally present registered merchant may buy at most one required ingredient per simulation tick. They see only actually posted, physically co-located quotes. They do not remotely search markets or leave the venue to scout. The selector can consider a purchase only if *all* missing ingredients for one actual site recipe are already locally offered and the entire missing batch is affordable from actual site copper after reserving all previously completed signed unpaid wages. Site-owned money never becomes keeper or cook personal cash. The authoritative `MarketTradeExecuted` event records the existing `business_keeper_id` business receipts and transfers physical ownership without minting anything.

A known, already-funded kitchen test fixture executes the two real source jobs, Huda's actual road trips and her physically posted two offers. Unlike PLAY49-G, no test driver explicitly tells the tavern keeper to buy either item; two actual independent `LivingWorldEngine.advance` calls now allow it to buy both site-owned items automatically. Negative cases prove default-off, one unavailable ingredient, and keeper in actual road transit. Existing H crop/milking third-plate test remains unchanged.

## Honest limitation

This is **only one autonomous business decision**, not autonomous planting, cattle care, transport, production scheduling, cooked meal posting, buyers' hunger behavior, replenished feed/water or continuous 96/168h economic endurance. Existing PLAY49-H demonstrated only one finite physically sourced third batch from explicitly initialized feed and water. No new event types or world schema versions were introduced in this branch; however its parent still carries PLAY49-G's persisted receipt addition, which needs historical save-compatibility testing.

Must pass exact-head targeted and full GitHub Actions on Python 3.10 and 3.13. Stay isolated, no main or PLAY48 merge, and keep this experiment gated on PLAY48 acceptance.
