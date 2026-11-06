# Phase 04-A / J1c2b — legal title feasibility and minimum implementation contract

**Opened:** 2026-11-06. **Status: ANALYSIS / DESIGN IN PROGRESS — NO CODE, SCHEMA CHANGE OR TITLE EVENTS YET.**

## Entry gate

J1c2a closed technically under the owner's explicitly revised independent-review deferral policy, see `phase_04a_j1c2a_closure_gate.md`. Its external review is deferred, not approved; P0 production recovery and unauthenticated network/player commands remain restricted. This design concerns isolated disposable-world engine development only.

## Problem to solve

A physical bread transaction (`MarketTradeExecuted`), taking (`PropertyTaken`), physical custody, J1a recorded origin, J1c1 permission, and J1c2a historical claim transfer are different facts. **None alone grants enforceable current legal title.** A title system needs (1) normative jurisdiction/rules, (2) legally meaningful assignment basis and time, (3) evidence of consent/capability, (4) treatment of theft and good-faith third parties, and (5) a disputed/unknown outcome instead of inventing a winner.

## Proposed deliberately narrow first executable slice (not yet approved as a law)

- One jurisdiction version per explicitly configured local site; no global or implicit inherited law, and no retroactive interpretation of old events.
- A **title assertion/record**, not automatically adjudicated legal title, may cite a real source event and a limited quantity. This is a legal *claim* under a configured rule, not a court verdict.
- Differentiate `unknown`, `uncontested recorded claim`, `disputed`, `settled by explicitly authorized process`. No omniscient lawful-owner field.
- No physical transfer, possession change, market money movement or restitution is triggered merely by writing or disputing a claim.
- Scope to one identifiable registered origin and non-fungible/traceable units where data permits; mixed indistinguishable bread **must be unresolved**, not silently allocated. Never produce more legally recognized quantity than provenance supports.
- Only trusted local authorized bootstrapping for jurisdiction configuration. Never accept free player-supplied role/authority flags from an untrusted API.
- A claimant's statement or sale record alone does not bind a non-consenting third party or defeat an earlier recorded right.
- Keep code/data version pinning, event-source provenance, immutable past, deterministic replay, fail-closed loads for old schema without explicit migration.

## Decisions required before creating a binding title event

1. **Jurisdiction**: initial authority will be local custom, council, lord, or other political institution? A jurisdiction must be explicitly installed in the world and scoped to a place; do not assume a universal court.
2. **Normative transfer rule**: does a consensual market sale transfer lawful title; under which seller entitlement and witness/consent criteria? Does transfer of a *historical claim* ever confer title? Default answer is **NO** until a rule is approved.
3. **Unlawfully removed objects / good-faith buyer**: competing owner, possessor, third-party buyer; unknown/disputed is allowed rather than automatic favoring.
4. **Evidence and disposition**: who may record declarations, object, and resolve claims, and what can the resolver actually know? No court/decision code until institutions J2/J3 are built and bounded.
5. **Title representation**: can the world attribute individual item lots accurately? Otherwise restrict the first slice to a record of conflicting claims, leaving title unresolved.
6. **Historical applicability**: configure rules prospectively with version and effective simulation time. Never infer title from legacy events without authorized migration/design.

## Proposed acceptance tests after approval, before implementation

1. Bakery records origin for two bread units; J1c2a assignment to Salma changes the historical claim ledger, but **does not** mint legal title.
2. Basim takes bread physically; possession/custody changes while legal status remains unknown/disputed.
3. Basim sells to Nora after taking; payment and inventory change, but Nora does not automatically receive enforceable title.
4. Two conflicting claims to the same mixed bread cannot both be granted an enforceable exclusive title; absence of provenance returns unresolved.
5. Invalid site, jurisdiction, actor, authorization, quantity, time, duplicate command or stale revision fail without modifying world.
6. Claim notice never communicates instantly to an absent NPC; gossip/claim does not create omniscient knowledge.
7. Snapshot/replay/full SQLite verification, duplicates and transactional rollback preserve exact provenance and prevent double allocation.
8. Genuine older world is rejected unchanged unless a tested migration has been separately designed; earlier feature-off behavior remains equivalent.
9. Backup + disposable-world restore verifies exact claim state and no physical inventory movement.
10. Both Python 3.10 and 3.13 specialized and full CI pass on exact final code SHA; external review deferred as stated by owner and external environment tests logged.

## Boundaries

**Explicitly excluded:** courts, trials, sentences, police powers, seizure, automatic restitution, legal punishments, fines, state taxes, appeals, fabricated witnesses, and omniscient verification. These require later J2–J5 decisions. No modification to `main` or original Carlos narrative files. No public network access or production save authorization.

## Immediate next engineering action

Perform a constrained audit of existing `market.py`, `rights.py`, `property.py`, `registered_claims.py`, and source-event schemas, then freeze a signed-off minimal normative jurisdiction and title representation contract. **Do not write binding title reducers or migrate Schema 28 / Rules 36 until normative rules are explicitly chosen and verified not to contradict world governance.**


## Initial source-contract audit (2026-11-06)

Read the actual current engine modules `market.py`, `rights.py`, `property.py`, and `registered_claims.py` on the J1 branch:

| Module | Verified contract | Title implication |
|---|---|---|
| `market.py` | Local offers and atomic physical goods/payment balance transfer; site stewards represent the **site's** stock | Payment and receipt are evidence of transaction only; do not determine legally valid title |
| `rights.py` | Trusted time-zero historical original claim, bounded by known registered stock, explicitly `historical_origin_only` | Does not establish contemporary title |
| `property.py` | Physically conserved non-consensual taking requiring an internal capability; no automatic guilt or confiscation | Changes possession, not legal status |
| `registered_claims.py` | Bounded recorded-claim balances, local offer/accept/cancel handshake and provenance | Transfers registered historical claim only, no physical or legal-title movement |

**Audit conclusion:** It would be an unsound implementation to auto-issue `CurrentLegalTitleTransferred` on any of these existing events. The first safe J1c2b implementation cannot be chosen until an explicit law authority, prospective effect, reliable lot identification and evidence/consent representation are fixed. The status is **DESIGN_IN_PROGRESS**, not code-complete; no unresolved audit item is hidden.
