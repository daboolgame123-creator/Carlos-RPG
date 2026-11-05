# Phase 01-X — Player perception and evidence-scoped memory

**Status:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED based on 615/615 tests per Python version on CI 42033754979. **NOT APPROVED/CLOSED.**
**Base:** validated 01-W commit `3fb18d3222ebdc08307d393bab8603a5726dda63`, CI [42021905506](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42021905506).
**Branch:** `simulation-engine-phase-01x`. **P0: OPEN**.

## Concrete gap
The 01-W `inspect()` displays only current location and present entities, but does not persist what Carlos actually looked at. It does not distinguish remembered local observations from messages reported by NPCs. Returning raw `WorldState` or NPC beliefs would violate the privacy boundary.

## Minimal implementation
- Keep `inspect()` strictly **read-only** and limited to present co-located entities/public exits. Add `observe(command_id, expected_revision)` for an explicit, player-selected `look`: records the exact current sorted occupant IDs under a trusted event and then returns a sanitized current view. During travel it cannot observe.
- Add `recall()` to read **only the player's own recorded sightings** (latest sighting per visited site) and **NPC messages explicitly delivered to that player**. Each memory has its original logical timestamp. Past occupancy does not become the present truth. Reconstruct from the event ledger after full `verify()`, not a parallel DB or other NPC memories. The demo's `remember` command calls this.
- A trusted NPC-side `NPCSocialService.share_food_claim_to_player` may deliver the named NPC's **existing food belief** to a co-located player. The player cannot force or call this NPC-side decision through `PlayerGateway`. No autonomous NPC-to-player speaking policy yet. An NPC cannot share unknown facts or hearsay received in the same tick.
- Delivered food claims are always labeled `unverified`. This is *testimony from a real actor*, not a live reading of hidden remote resources; a stale or false claim stays fallible.

## New event contracts
1. `PlayerObserved`: `actor_id` is a player. Payload exactly `{location_id, occupants}` and reducer verifies location and sorted visible occupants against co-location and travel rules at event time. Requires trusted `movement_authorized` and active session.
2. `PlayerHearsayReceived`: `actor_id` is the NPC speaker; payload exactly `{player_id, key, text}`. The recipient is a present player at the same location and the text equals a real currently held `food:<site>` belief of that NPC. Requires trusted `social_authorized` and active session. The source and logical time come from the event envelope. No automatic NPC belief adoption by the player.

The event reducer validates both types without exposing or mutating foreign inventories, intentions, trust or resources. Only recorded observations and personally addressed claims appear in recall output. CLI keeps using a disposable SQLite database.

## Schema / Rules / compatibility
**Schema stays 13. Rules rises from 19 to 20** because 01-X adds event types with mandatory replay-time checks. World snapshot shape is unchanged; player memory is event-derived. A genuine 13/19 database must be rejected by 13/20, unchanged; no silent migration. The CI workflow checks a genuine 01-W database and its metadata/event/snapshot counts. Full replay, snapshots, close/reopen, integrity, spoofing, travel, identity, and command-id tests must pass on Python 3.10 and 3.13.

## Explicit exclusions
No hidden NPC intentions, global visibility, automatic truthful rumor interpretation, unprompted NPC speech, player knowledge of arbitrary claims, local-server authentication, health/combat/inventory/quests/skills, performance optimization for years-long archives, permanent saves, or imports of real Carlos story facts. P0 backup/restore remains OPEN.

**Technical-only acceptance:** all new and inherited tests pass at the same final commit. Independent approval is not claimed.
