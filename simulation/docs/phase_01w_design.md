# Phase 01-W — Local player command gateway (provisional technical design)

**State:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED — NOT APPROVED/CLOSED. Work on `simulation-engine-phase-01w`; parent tested Phase 01-V correction `6a0f3d473f0eecb856fb2b320e1d6485b032b3bc`. Original OpenCode BLOCKED findings for old 01-T/01-U SHAs remain recorded. Main and narrative files protected.

## Intent and trust boundary

- A **trusted local** Python `PlayerGateway` owns exactly one configured `controller='player'` entity for exactly one world. Local scripts call `move`, `wait`, `inspect` and `interact` as explicit player commands. No automatic choice of Carlos's commands, no simulated NPC personality assigned to Carlos, no arbitrary entity control or public/network authentication.
- `inspect` exposes only *local, public* place/occupant/exits data and the player's own travelling progress; it never returns `WorldState`, resources, NPC beliefs, full graph, hidden schedules, obligations or secrets. Stronger perception and visibility logic remains 01-X.
- `interact` adapts existing event-backed `NPCSocialService` for a player speaker and co-located NPC recipient. Allow only the existing four speech acts, with strict target/text/input checks. No forced NPC outcome: existing NPC reaction is authoritative.
- `wait` invokes existing `LivingWorldEngine.advance` (injectable, with one shared clock/store) to progress real time and NPC autonomy; returned data are sanitized, not the full world. It must not choose a player action.
- `move` must not teleport or create shortcuts. Validates player identity, an *incident route* and absence of current player travel; registers a trusted scheduled `__player_travel` signal with `due=now+route.seconds`. **The player remains at origin** until `ScheduledEventFired` completes movement. While in transit, player cannot speak or begin a second journey; an inspect returns travelling progress only. On arrival, the player location changes exactly once and becomes visible locally.
- At most one active scheduled player trip per player. The payload contains `player_id, route_id, origin, destination, started_at`; the schedule carries `due`, the exact travel time. Strict validation at event projection, player state snapshot validation and trusted clock firing. A fake schedule cannot move an NPC or a different player.
- No `PlayerCommand` persisted command language, arbitrary model-generated command text, public HTTP, secrets, items, quests, combat, XP, or player-directed NPC decisions. A structured local gateway is the only new facade.

## Versioning: deliberate nonportable Rules upgrade

- New meaning of `ScheduledEventCreated` / `ScheduledEventFired` and player transit/presence semantics requires **Schema 13 / Rules 19**. Old **13/18** worlds must fail closed `UnsupportedVersion` without altering any original bytes or rows. Do not reinterpret or migrate them in place; no migration tool in 01-W. Keep frozen prior-version runtime benchmarks for events and semantic parity **only where explicitly version-neutral**, not by pretending old worlds are upgraded.
- New tests must verify an actual 01-V (13/18) saved SQLite file is rejected without mutation, including events, snapshots and world metadata; prove restore of current 13/19 snapshots, deterministic event replay, and no automatic P0 certification.

## Acceptance matrix

1. An NPC and a player can co-exist. NPC planning never controls player. A player is not listed as an NPC and cannot issue NPC-only service operations.
2. Inspect lists only present players/NPCs and incident roads at current location; no foreign truth; while travelling reveal only the player's route, eta and in-transit status, never remote occupants.
3. Move has a durable scheduled signal, no pre-arrival teleport, exact 1-second-before/at-due behavior; valid two-hop travel needs two explicit player move commands, cannot choose unseen/nonadjacent route.
4. A second move/interaction while in transit, invalid actor, remote NPC interaction, unsupported kind, bad IDs, stale revision and closed session fail with no partial event, item transfer, or state leak.
5. Real player social interaction records `SocialMessageSent` and `SocialMessageReceived` and changes only recipient's permitted reaction; repeated command must not mint extra trust.
6. Wait drives NPCs with existing rules but does not select Carlos's choices. An event-budget failure leaves both time and player movement state and event log unchanged (atomic batch).
7. Snapshot/SQLite close-reopen/full `verify` match; order of player arrival vs due NPC events is deterministic; prior 01-V code stays isolated in an immutable branch.
8. Full Python 3.10 / 3.13 CI, frozen predecessor compat rejects actual 13/18 worlds; **EXTERNAL_REVIEW_DEFERRED** and **P0 OPEN** documented.

**Special note:** This is a trusted *local Python application* facade. Binding `player_id` in a Python object is **not** authentication or network authorization. Never expose store or capability flags to an untrusted client.

**Implementation evidence:** [01-W report](phase_01w_report.md) and [review handoff](phase_01w_review_request.md); code SHA `8787cf549973d78b1fc471fc86858b23aa422840`; [CI 42021241326](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42021241326) **607/607** each on Python 3.10 and 3.13. No independent approval, no P0 closure.
