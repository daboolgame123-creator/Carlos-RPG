# PLAY49-I actual saved-world compatibility diagnostic (PREP ONLY)

Source branch `experiment/play49-i-autonomous-tavern-procurement-20261117`, exact parent `8a18524e9d5aa0c352212c9bff304fd3c29be524`. Separate read-only engine diagnostic branch. **Never merge this branch into PLAY48 or main.**

A persistent trade receipt was extended with `business_keeper_id` in PLAY49-G, but the genuine pre-G commit `5464f12efacc825fdd8bf1fb03b8d773b9f65935` and I still both report `SCHEMA_VERSION=45`, `RULES_VERSION=70`. The previous market-trade validator only accepts the old receipt field set.

This CI checks:
1. I writer genuinely produces two new site-owned purchases and verifies/snapshots its SQLite database.
2. The **frozen old-code reader** (not just a stub validator) tries full genesis replay of the newer saved world; the expected diagnostic is `IntegrityError` despite matching claimed versions, without mutating saved bytes.
3. The real pre-G writer creates an actual old world at 45/70; the new reader verifies that saved world, byte-identically.

A GREEN diagnostic run means **the incompatibility was detected**, NOT that it was fixed. If unexpectedly compatible, the asserted old-reader failure makes the diagnostic RED for fresh investigation.

**Required before release:** versioned compatibility decision for this persisted rule, proper migration or explicit refusal contract, old-code writer + reader matrix, exact-head tests. Existing PLAY49-I full regression is a separate gate. Status `PLAY49_I_COMPAT_AUDIT / RELEASE_NO_GO`.
