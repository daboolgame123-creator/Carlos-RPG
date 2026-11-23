"""P10: authentic P7 h234 two-arm P9 baseline versus hunter-assisted Huda.

P9 remains active in BOTH arms; only P10 hunter visiting differs. Independent
copied SQLite histories, actual road travel, receipt-authenticated owned food,
signed wages and unchanged 12 copper. No seeded rescue or teleportation.
"""
import hashlib
import json
from pathlib import Path

import play48_real234_physical_courier_aid as p9

OUT = Path("real234_hunter_huda")


def main():
    source_matches = sorted(p9.SOURCE.rglob("P7_signed_wage.sqlite"))
    assert len(source_matches) == 1, source_matches
    source = source_matches[0]
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    p9.OUT = OUT
    a = p9.run_arm(source, "P9_control", True)
    b = p9.run_arm(source, "P10_hunter", True, hunter_visit=True)
    assert original == hashlib.sha256(source.read_bytes()).hexdigest()
    for hour in (235, 236, 240):
        old, new = a[str(hour)], b[str(hour)]
        delta = {
            "hour": hour, "huda_hunger_delta":
                new["huda"]["hunger"] - old["huda"]["hunger"],
            "huda_delivery_delta":
                new["deliveries"]["huda"] - old["deliveries"]["huda"],
            "hana_deliveries": new["deliveries"]["hana"],
            "new_meals": new["meals"] - old["meals"],
            "new_hunger100": new["starving"] - old["starving"],
            "copper_control": old["copper"],
            "copper_candidate": new["copper"],
            "original_sha256": original, "release_gate": "PLAY48_NO_GO",
        }
        print("PLAY48_P10_HUNTER_VS_P9 " + json.dumps(delta, sort_keys=True), flush=True)
        assert old["copper"] == new["copper"] == 12
        assert new["starving"] <= old["starving"]
    receipts = b["240"]["authentic_physical_aid"]
    help_huda = [v for v in receipts.values()
                 if v["donor"] == "omar"
                 and v["requester"] == "huda" and v["status"] == "fulfilled"]
    assert len(help_huda) == 1, "No real hunter-to-Huda witnessed food transfer"
    gift = help_huda[0]["transfer"]
    assert gift["provider_before"] - gift["provider_after"] == 1
    assert gift["requester_after"] - gift["requester_before"] == 1
    assert b["240"]["huda"]["meals"] > a["240"]["huda"]["meals"]
    assert b["240"]["huda"]["hunger"] < a["240"]["huda"]["hunger"]
    assert b["240"]["deliveries"]["huda"] > a["240"]["deliveries"]["huda"]
    assert b["240"]["deliveries"]["hana"] >= a["240"]["deliveries"]["hana"]
    (OUT / "comparison.json").write_text(json.dumps({
        "source_sha256": original, "control": a, "candidate": b,
        "release_gate": "PLAY48_NO_GO"
    }, indent=2, sort_keys=True), encoding="utf8")


if __name__ == "__main__":
    main()
