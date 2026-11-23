"""P11 experimental in-person wage for authenticated Huda grain courier work.

The SAME original P7 h234 SQLite history is copied twice. Both branches have P9
Hana and P10 Huda rescue enabled. Only the P11 local market wage flag differs.
No new stock, roads, currency, employment bootstrap or remote work.
"""
import hashlib
import json
from pathlib import Path
import play48_real234_physical_courier_aid as p9

OUT=Path("real234_huda_food_wage")

def main():
    src=sorted(p9.SOURCE.rglob("P7_signed_wage.sqlite"))
    assert len(src)==1,src
    old_hash=hashlib.sha256(src[0].read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    p9.OUT=OUT
    old=p9.run_arm(src[0],"P10_rescue_only",True,hunter_visit=True)
    new=p9.run_arm(src[0],"P11_real_wage",True,hunter_visit=True,market_wage=True)
    assert hashlib.sha256(src[0].read_bytes()).hexdigest()==old_hash
    for hour in (235,236,240):
        a,b=old[str(hour)],new[str(hour)]
        record={
            "hour":hour,
            "huda_food_wage_count":b["huda_freight_wages"],
            "huda_meal_delta":b["huda"]["meals"]-a["huda"]["meals"],
            "huda_hunger_delta":b["huda"]["hunger"]-a["huda"]["hunger"],
            "huda_delivery_delta":b["deliveries"]["huda"]-a["deliveries"]["huda"],
            "combined_courier_delta":sum(b["deliveries"].values())-sum(a["deliveries"].values()),
            "starving100_delta":b["starving"]-a["starving"],
            "coin":b["copper"],"gate":"PLAY48_NO_GO",
        }
        print("PLAY48_P11_MINUS_P10 "+json.dumps(record,sort_keys=True),flush=True)
        assert b["copper"]==a["copper"]==12
    contract=new["240"]["huda_contract"]
    assert contract is not None and contract["signed_at"] >= 234*3600
    proof=contract.get("initial_grain_service")
    assert proof is not None and proof["delivery"]==22
    assert any(x["payment"] is not None for x in contract["receipts"]), "no actual owned food paid for documented service"
    first=next(x for x in contract["receipts"] if x["payment"] is not None)
    assert first["payment"]["source_before"]-first["payment"]["source_after"]==1
    assert first["payment"]["worker_after"]-first["payment"]["worker_before"]==1
    assert new["240"]["huda"]["meals"]>old["240"]["huda"]["meals"], "no consumed earned wage"
    assert new["240"]["huda"]["hunger"]<old["240"]["huda"]["hunger"], "wage did not improve worker's real hunger"
    # A paid courier must not block an already signed, source-owned,
    # physically co-present community ration by resetting quote age.
    assert new["240"]["starving"]<=old["240"]["starving"], (
        "wage-driven market re-listing denied an existing real ration")
    (OUT/"comparison.json").write_text(json.dumps({
        "origin_sha256":old_hash,"control":old,"candidate":new,
        "status":"PLAY48_NO_GO"},indent=2,sort_keys=True),encoding="utf8")

if __name__=="__main__":
    main()
