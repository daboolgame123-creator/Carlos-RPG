# Carlos RPG — J1c2b-LAW: decision brief (non-binding)

Date: 2026-11-06
Status: ANALYSIS_COMPLETE / OWNER_DECISION_REQUIRED / NO_RULE_OR_SCHEMA_CHANGE
Branch: `simulation-engine-phase-04a-j1`
Dependencies: J1c2b-CI and J1c2b-REG technically closed on code SHA `88c110e1c77d724424eb105a3fea0dd6d541bd3e`; authority/title policy remains undefined.
Scope: isolated simulation worlds only. No production approval.

## What already exists

- `LocalInstitutionRegistered` records an institution's existence at a real site with a real local representative, under trusted time-zero bootstrap.
- Its mandate is **existence_record_only**. Representation is not a judge, ruler or authorization credential.
- Existing physical possession, market trade, provenance, registered historical claim and allegations are **distinct**. None determines enforceable title.
- Trusted-only read-only evidence reports are not suitable for unfiltered player/NPC/LLM access.

## Decision points — do not infer consent

| ID | Question for owner | Conservative candidate for discussion | Must stay prohibited until approval |
| --- | --- | --- | --- |
| LAW-01 | Who can establish a **local** jurisdiction? | A locally constituted council with explicitly recorded, narrowly scoped rule-making authority; a lord/assembly remains another optional model. | A registered institution gaining power from existence alone. |
| LAW-02 | How does the institution receive authority? | Separate prospective charter event with trusted issuer, stated jurisdiction, mandate, effective time and audited authorization. | Accepting arbitrary player-supplied role/issuer claims. |
| LAW-03 | Does a consensual trade transfer legal title? | Only if verified prior title, individually traceable goods, seller capacity, buyer/seller consent and an effective local rule are all proven. | Declaring ownership from payment, possession or historical claim alone. |
| LAW-04 | What happens when proof is incomplete or goods are mixed? | Return **unknown / disputed**; preserve competing claims and evidence, without winner or physical restitution. | Fabricating lot identity or awarding more units than traceable origin. |
| LAW-05 | Can a purported good-faith buyer defeat a prior claimant? | No automatic priority pending explicit prospective law and evidence rules. | Retroactively stripping a recorded interest. |
| LAW-06 | Who can resolve disputes? | No adjudication in J1c2b. Defer court competence, hearings and rulings to a separately approved J2+ contract. | Court verdict, arrest, fines, seizure or automatic penalties. |

These are **options and safe defaults for discussion, not adopted in-world law**.

## Proposed bounded implementation order after explicit decisions

1. Freeze signed-off authority model, issuer trust boundary, jurisdiction scope and non-retroactive effective time.
2. Establish a trusted versioned authority charter event, with tests for forged issuer, wrong site, forged representative, stale revision and rollback. Do not reuse `LocalInstitutionRegistered` as its own authority grant.
3. Build deterministic provenance and consent checks for **traceable lots only**; preserve unknown results for fungible stock.
4. Record proposed title assertion with cited source events and bounded quantity; a recorded assertion must not automatically become enforceable ownership.
5. Introduce any enforceable transfer only under explicit approved rule and reliable current title evidence. Keep dispute resolution out of scope unless separately approved.

## Tests required before technical closure

- Forged authority/issuer/consent rejects with byte-for-byte unchanged world and event log.
- Nonlocal representative and duplicate institution/charter reject without mutation.
- Prior physical theft followed by sale does not silently create lawful title.
- Historical claim assignment alone changes no legal owner.
- Mixed bread stock stays unresolved, with no double allocation across origins.
- Prospective jurisdiction does not rewrite old events or imply retroactive title.
- Character knowledge remains filtered by perception/information channels.
- Replay, snapshot, SQLite reopen and backup/restore are deterministic; old-version file rejects unchanged unless separately migrated.
- Full Python 3.10/3.13 regression, adversarial gates and parity pass on the exact final SHA.

## Outstanding gates

- `J1c2b-LAW`: DECISION_REQUIRED / WAITING_DECISION; **no binding legal-title event or current lawful owner**.
- `EXT-001`: independent adversarial review deferred by owner, not approved.
- `EXT-002` and `EXT-003`: real production / target-Windows restore still require external validation.
- `EXT-004`: network/player authentication not implemented; do not expose untrusted commands.

This brief changes documentation only. It is not legal authority, user approval, code verification or phase closure.
