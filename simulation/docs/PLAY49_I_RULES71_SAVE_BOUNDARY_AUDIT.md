# PLAY49-I — candidate Rules71 save boundary (audit only)

Date: 2026-11-17. Parent is the exact tested PLAY49-I commit `8a18524e9d5aa0c352212c9bff304fd3c29be524`; this branch is strictly isolated from PLAY48 and main.

## Why

PLAY49-G introduced a new persisted `MarketTradeExecuted` receipt form with a `business_keeper_id` and authorization for genuine site-wallet purchases. The pre-G reader and the new writer both advertised `Schema45/Rules70`, even though the pre-G reader cannot replay this receipt. Real frozen pre-G reader CI on audit PR #146 proved `IntegrityError: corrupt event 168` on a new valid world saved under Rules70. No money or food was minted; this is a **version-contract defect**.

## Candidate fix

Keep `SCHEMA_VERSION=45` because SQLite/world field layout did not change, and raise `RULES_VERSION` to **71** because replay meaning and authorized event shape did. Update the independent `release_contract.py` expected writer version to 45/71.

The cross-reader gate builds a genuine Rules71 tavern with both newly authorized market purchase receipts and checks replay + snapshot + exactly 22 copper. It then opens the same database with the actual frozen pre-G Rules70 reader and asserts **UnsupportedVersion** before replay, no mutation, no misleading `corrupt event`. A second genuine Rules70 file is generated with the pinned old writer, and the Rules71 reader must refuse it immutably. All checks run on Python 3.10/3.13; exact-head full simulation CI is additionally required.

This is **not** a migration. Rules70 preserved worlds cannot be loaded into Rules71 without a separately approved migration and recovery proof. Never bump the version header in-place or silently reinterpret old history. The LIVE PLAY48 code line is independently developing Schema45/Rules70, so any eventual merger requires reconciliation with PLAY48's newer rules and a real base-side compatibility review. No automatic merge, release or long-lived-world guarantee is authorized.

**Status: DRAFT / AUDIT_ONLY / PLAY48_OPEN / RELEASE_NO_GO**.
