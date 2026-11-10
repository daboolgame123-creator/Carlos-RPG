"""CI-04b research-only head-snapshot verification A/B.

A candidate algorithm is evaluated WITHOUT modifying carlos_sim/store.py.
No optimization may be deployed based only on this bounded experiment.
"""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import tempfile
import time

from carlos_sim import SQLiteEventStore
from carlos_sim.domain import canonical, canonical_hash
from carlos_sim.store import IntegrityError
from test_play47_closure_endurance import _day, _seed, WORLD


def candidate_verify(store: SQLiteEventStore, world_id: str):
    """Proof candidate: validate full history once, and the head snapshot directly.

    For any non-head/missing snapshot, call the existing production verify.
    This private-API prototype intentionally does not replace production code.
    """
    row = store._world_row(world_id)
    snap = store.db.execute(
        "SELECT revision,state,hash FROM snapshots "
        "WHERE world_id=? ORDER BY revision DESC LIMIT 1",
        (world_id,),
    ).fetchone()
    if snap is None or snap[0] != row[0]:
        return store.verify(world_id)
    full = store.load(world_id, use_snapshot=False)
    saved = store._decode_state(snap[1], snap[2])
    if saved.world_id != world_id or saved.revision != snap[0] or snap[0] > row[0]:
        raise IntegrityError("head snapshot identity/revision mismatch")
    if canonical_hash(saved.to_dict()) != canonical_hash(full.to_dict()):
        raise IntegrityError("head snapshot and full replay disagree")
    return full


def require_same_rejection(store, world_id: str, label: str) -> None:
    for method in (store.verify, lambda w: candidate_verify(store, w)):
        try:
            method(world_id)
        except IntegrityError:
            pass
        else:
            raise AssertionError("unacceptable corruption accepted: " + label)
    print("CI04B_REJECTION", label, flush=True)


def corruption_parity(store: SQLiteEventStore, world_id: str) -> None:
    snap = store.db.execute(
        "SELECT revision,state,hash FROM snapshots WHERE world_id=? "
        "ORDER BY revision DESC LIMIT 1", (world_id,),
    ).fetchone()
    assert snap is not None

    try:
        store.db.execute(
            "UPDATE snapshots SET hash=? WHERE world_id=? AND revision=?",
            ("00", world_id, snap[0]),
        )
        require_same_rejection(store, world_id, "snapshot_hash")
    finally:
        store.db.execute(
            "UPDATE snapshots SET hash=? WHERE world_id=? AND revision=?",
            (snap[2], world_id, snap[0]),
        )

    state = json.loads(snap[1])
    state["time"] += 1
    changed = canonical(state)
    changed_hash = canonical_hash(state)
    try:
        store.db.execute(
            "UPDATE snapshots SET state=?,hash=? WHERE world_id=? AND revision=?",
            (changed, changed_hash, world_id, snap[0]),
        )
        require_same_rejection(store, world_id, "valid_digest_inconsistent_semantics")
    finally:
        store.db.execute(
            "UPDATE snapshots SET state=?,hash=? WHERE world_id=? AND revision=?",
            (snap[1], snap[2], world_id, snap[0]),
        )

    event = store.db.execute(
        "SELECT seq,hash FROM events WHERE world_id=? ORDER BY seq LIMIT 1",
        (world_id,),
    ).fetchone()
    assert event is not None
    try:
        store.db.execute(
            "UPDATE events SET hash='00' WHERE world_id=? AND seq=?",
            (world_id, event[0]),
        )
        require_same_rejection(store, world_id, "event_receipt_hash")
    finally:
        store.db.execute(
            "UPDATE events SET hash=? WHERE world_id=? AND seq=?",
            (event[1], world_id, event[0]),
        )

    # With a non-head snapshot, the candidate must not skip suffix replay.
    try:
        store.db.execute(
            "UPDATE snapshots SET revision=revision-1 WHERE world_id=? AND revision=?",
            (world_id, snap[0]),
        )
        require_same_rejection(store, world_id, "snapshot_revision_forgery")
    finally:
        store.db.execute(
            "UPDATE snapshots SET revision=? WHERE world_id=? AND revision=?",
            (snap[0], world_id, snap[0]-1),
        )
    assert store.verify(world_id).to_dict() == candidate_verify(store, world_id).to_dict()


def time_ab(store: SQLiteEventStore, world_id: str, rounds: int = 3) -> dict:
    measured: dict[str, list[float]] = {"baseline": [], "candidate": []}
    functions = {"baseline": store.verify, "candidate": lambda w: candidate_verify(store, w)}
    reference = store.verify(world_id).to_dict()
    for i in range(rounds):
        order = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
        for name in order:
            start = time.perf_counter()
            observed = functions[name](world_id).to_dict()
            elapsed = time.perf_counter() - start
            assert observed == reference, (name, i, "world state changed")
            measured[name].append(elapsed)
    base = statistics.median(measured["baseline"])
    candidate = statistics.median(measured["candidate"])
    return {
        "baseline_median_seconds": round(base, 6),
        "candidate_median_seconds": round(candidate, 6),
        "candidate_vs_baseline": round(candidate / base, 4),
        "rounds_per_variant": rounds,
        "revision": reference["revision"],
        "world_id": world_id,
        "same_full_state": True,
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ci04b-replay-ab-") as dirname:
        path = Path(dirname) / "play47-6h.sqlite"
        _seed(path)
        built = _day(path, 6 * 3600)
        with SQLiteEventStore(path) as store:
            assert store.verify(WORLD).to_dict() == built.to_dict()
            assert candidate_verify(store, WORLD).to_dict() == built.to_dict()
            result = time_ab(store, WORLD)
            corruption_parity(store, WORLD)
            # Missing snapshot must fall back, not silently assume integrity.
            store.db.execute("DELETE FROM snapshots WHERE world_id=?", (WORLD,))
            assert store.verify(WORLD).to_dict() == candidate_verify(store, WORLD).to_dict()
            result["no_snapshot_fallback"] = True
            result["rejections_agree"] = 4
            result["schema_changed"] = False
            result["engine_modified"] = False
            result["performance_patch_applied"] = False
            result["production_recommendation"] = "REVIEW_ONLY"
            print("CI04B_AB_SUCCESS " + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
