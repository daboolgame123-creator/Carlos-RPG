# OpenCode — models and reasoning-effort inventory (user-provided screenshots, 2026-11-09)

**Source:** Screenshots supplied by the project owner of model/effort selection menus in OpenCode. Names are transcribed as shown, **not** a live model API or confirmation of current quotas, price, latency, API entitlements, capability rankings or which effort tiers each model actually accepts. Recheck the selector before delegating; an account UI may change without a repository commit.

## 1. Exact visible model labels

### Screenshot group A (10)
1. `GPT-5.5`
2. `GPT-5.5 Fast`
3. `GPT-5.6 Luna`
4. `GPT-5.6 Luna Fast`
5. `GPT-5.6 Sol`
6. `GPT-5.6 Sol Fast`
7. `GPT-5.6 Terra`
8. `GPT-5.6 Terra Fast`
9. `GPT-6 Astra`
10. `GPT-6 Astra Fast`

### Screenshot group B (8)
1. `GPT-6 Luna`
2. `GPT-6 Luna Fast`
3. `GPT-6 Sol`
4. `GPT-6 Sol Fast`
5. `GPT-6.1 Sol`
6. `GPT-6.1 Sol Fast`
7. `GPT-6.1 Terra`
8. `GPT-6.1 Terra Fast`

**Visible effort menu:** `افتراضي` (Default), `Low`, `Medium`, `High`, `Xhigh`, `Max`; `Favorite` is a preference shortcut, **not** another thinking effort. Use the exact capitalized names `Xhigh` and `Max` shown by the owner. Availability and behavior for each model/effort pair must be confirmed in OpenCode; do **not** claim universal Low→Max compatibility.

## 2. Proposed model/effort routing — benchmark, don't assume superiority

| Job type | Initial candidate(s) in OpenCode | Initial effort | Escalate only if |
|---|---|---|---|
| Short docs, git metadata, test summaries, handoff, simple fixtures | GPT-5.5 Fast; GPT-5.6 Luna Fast; GPT-6 Luna Fast | Low / Medium | Requirements contain nontrivial invariants |
| Isolated feature logic and targeted deterministic tests | GPT-5.6 Sol; GPT-6 Sol; GPT-6.1 Sol | Medium / High | Repeated failing acceptance cases |
| Cross-module integration: NPC planning, physical trade, clock partitions, ledger/replay | GPT-5.6 Terra; GPT-6.1 Terra; GPT-6 Astra | High | Several competing root causes or novel persistent contracts |
| Adversarial independent review of persistence, ownership and trust boundary | GPT-6.1 Terra; GPT-6 Astra, distinct from builder when feasible | High / Xhigh | Concrete safety blocker needs deeper examination |
| Hard architecture or unresolved root cause after reproducible CI failures | GPT-6 Astra; GPT-6.1 Terra | Xhigh; Max **only for exceptional blocker** | Evidence shows lower-effort attempts did not resolve it |
| Fast prototypes before formal validation | The visible `Fast` variant corresponding to chosen candidate | Low / Medium | Tests fail or scope expands |

These are *routing hypotheses*, not guarantees that GPT-6 Astra or GPT-6.1 Terra is universally better than any other model; use actual results to update. `Fast` is only the visible label, **not** a validated speed/cost estimate.

## 3. Budget/quality experiment

1. Select 3 representative project tasks: a small isolated test fix, an economy/NPC integration problem, and a replay/security audit.
2. For each eligible candidate, record actual input/output tokens, tool calls, elapsed effort if available, first-pass test success, defects caught and human review needed. Never invent token quotas or per-model prices.
3. Reuse simpler/cheaper demonstrated options for routine work. Reserve High, Xhigh, and especially Max for cases with measurable complexity/risk.
4. Use GitHub Actions and deterministic pytest as ground truth, not model confidence; do not call a model's own review “independent sign-off.”
5. Spend model allowance dynamically, not a fixed percentage split. Do not send the same problem to multiple expensive agents without a clear evaluation hypothesis.
6. Follow the repository's no-self-merge, stage dependency, old-save refusal, P0 and external-review rules.
