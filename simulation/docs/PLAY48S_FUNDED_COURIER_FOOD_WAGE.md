# PLAY-48S — same-resource, actually earned courier meals

**Stage:** PLAY48_OPEN / RELEASE_NO_GO, Schema 43 / Rules 58, no production release or saved-state migration. **Status:** Experimental; actual CI result must be checked per exact SHA. **Branch:** `experiment/play48s-authentic-courier-food-wages-20261111`.

## Test-world causal intervention

The reviewed 48R fertile eastern field creates real grain with a 24h maturation period; 48R verified that more grain increased actual baking but not individual meals (six meals in both arms at 48h, four residents at hunger 100). Therefore **stop raising productivity to try to solve distribution**.

PLAY-48S uses the already implemented physical, *one-time* courier food provision ledger. The entire 13-NPC employment world continues: woodcutter, charcoal maker, first+east farmers, smith/repairer, baker, merchant, two couriers. Both A/B arms start with precisely the same trusted genesis, real food and money:

- Existing three opening loaves are owned **farm=1, market=2**; genuine employers escrow **one at farm for Huda** upon a real local **water** delivery, **one at market for Hana** upon actual supply service. One remains available for purchase. Total food including escrow stays **3**, not 5, and known copper stays **12**. Neither courier receives food for arriving, standing idle, an invented delivery, or a trip through a fake route.
- All food transfers must use the existing authenticated reducer and receipt log; payer-owned escrow was debited at trusted time zero, and the courier obtains a personally owned food unit only after actual labor. No eating consigned cargo or private wallet forged from company receipts.
- **Only A/B difference** is existing `early_courier_food_wage_enabled` payment timing, with fully identical 13 residents, existing water and authenticated rainfall, 12-copper ledger, eastern-fertile 12-grain recipe, road graph, wood and charcoal jobs. Other existing worker and known-supplier flags are the same in both arms.
- A physically separate **12h** check proves the paid water delivery and reject-forgery checks. A fully independent **48h** A/B reports real wages, deliveries, resident meals, bread sales, inventory and hunger. SQLite event replay and integrity checks apply.

**Caution:** This is not a sustainable wage cycle. Each two pre-funded entitlements is exhausted after at most one real delivery per worker. A green test proves the tiny honest contract works, *not* that baker profits were recycled, post72 work reactivated, or all residents survive 168h.

## Evidence gates

- [CI workflow for PLAY-48S](https://github.com/daboolgame123-creator/Carlos-RPG/actions/workflows/play48s-paid-courier-food.yml), initial test commit `eebd0a33d31e319efdc367b712a21a3da5efbda8`; **never mark SUCCESS until both Python 3.10/3.13 and end-to-end 48h stages finish**.
- Base PLAY-48R real 48h A/B [run 42919278865](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42919278865): SUCCESS both Pythons. The full 48R regression [run 42919617997](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42919617997) remains a distinct gate and must be checked.
- Next: distinguish one-time prevention from *repeatable* income and owned food access; implement post-production employer-funded replenishment only after explicit design review and appropriate rules/versioning, protect transactional provenance, compare at hours 72, 96 and 168, and preserve drought/insolvency failure cases.

No merge to `main`; do not start PLAY-49; do not infer any happy economic outcome from test success alone.
