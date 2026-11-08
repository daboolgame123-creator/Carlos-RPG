# PLAY-43 — Physical owned workshop input transfer

Branch is stacked on technically closed PLAY-42, not on main. No auto-merge.

Proof chain: finite initial two-grain farm ledger -> a buyer walks a real
60-second road -> an on-site farmer posts a legitimate grain offer -> the baker
spends two already-owned copper and takes one personally-owned grain unit ->
the baker physically returns -> one strict WorkshopMaterialDeposited event
atomically debits personal carried grain and credits bakery input -> the baker
performs a real 90-second grain-to-bread recipe -> a real customer buys a loaf
from bakery site stock -> the bakery can pay an agreed two-copper wage using
those exact sale proceeds. Total opening copper remains four.

The new material deposit cannot borrow currency, create material, act remotely,
cross actor identities, exceed stock, accept uninitialized balances or bypass
active play. It requires both existing persisted market and production command
capabilities to avoid new untracked SQLite authority columns. The event itself
is immutable, hashed, and audit/replay verified.

Rules increment from 55 to 56 because a new domain event becomes recognized.
Schema remains 41 because persistent WorldState fields are unchanged. Old 41/55
files must reject without mutation; no silent version upgrade. Existing worlds
need a separately reviewed migration if preserving prior saves is required.

Caveat: finite bootstrap grain is real owned opening inventory but this patch
does not prove a fresh autonomous grain harvest nor an autonomous intershop
purchase plan. Those are separate follow-up tasks. No carpenter/blacksmith
shop or item has been claimed as implemented.


## Cargo reservation hardening and genuine predecessor

An NPC's resources may temporarily include one parcel physically carried for
a courier's customer. The workshop event now subtracts that one reserved cargo
unit from the depositor's personal available amount. Only genuine additional
surplus can enter the workshop. An adversarial projector-only test checks
reservation without presenting a forged state as a valid end-to-end courier
journey.

The dedicated CI checks out the exact genuine PLAY-42 commit, creates an
actual SQLite Rules55/Schema41 file with that predecessor, and confirms the
PLAY-43 Rules56 engine rejects it without mutating metadata, byte digest or
database integrity.
