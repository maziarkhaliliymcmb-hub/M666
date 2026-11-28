# M666 Interoperability Contract 1.0.0

## 1. Authority and boundaries

- **M36** is the shared 36-gene identity space. The protected root genome is the authority for stable gene identifiers and their order.
- **M666** models symmetric association between genes, including self-relations. It does not model direction.
- **M1296** models directed source-to-target influence. Reverse edges are independent.
- **36OS-database** is the canonical runtime and governance service. It owns the database, authentication, proposal ledger and audit trail.
- M666 and M1296 packages are computational components. They do not connect directly to the 36OS PostgreSQL/Supabase database and do not approve or activate proposals.
- CIE and other consumers access genome data only through authenticated 36OS APIs.

## 2. Shared M36 identity and index mapping

All M666 and M1296 numeric endpoints use a zero-based index over the flattened M36 root genome:

1. Chromosomes ordered by `chromosome.index` ascending (1 through 6).
2. Genes within each chromosome ordered by their array position (1 through 6).
3. Stable identifiers are `M36-CHR01-G01` through `M36-CHR06-G06`.
4. The resulting numeric indices are 0 through 35.

The consumer must read `GET /v1/genome/root` and pin `genome.genome_id` and `genome.genome_version` before translating stable gene IDs to numeric indices. The expected root ID is `M36-ROOT`; the response must contain exactly 36 genes. A changed root version requires revalidation before interpreting stored indices. Do not silently reorder genes.

M666 and M1296 currently expose numeric indices, not stable gene IDs, in their registry payloads. Consumers must retain the M36 root version alongside any cached index-based snapshot.

## 3. M666 mathematical and record contract

- Address space: `C(36,2) + 36 = 666`.
- Canonical pair order: `0 <= gene_a <= gene_b < 36`.
- `(a,b)` and `(b,a)` resolve to one M666 slot.
- Diagonal pairs `(i,i)` represent self-relations.
- Registry storage is sparse. Capacity 666 does not mean 666 rows exist.
- `relation_type`: `synergy | dependency | conflict | inhibition | regulation | complementarity | neutral`.
- `weight`: numeric in [-1, 1].
- `confidence`: numeric in [0, 1].
- Weight and confidence must be evidence-backed; neither is inferred by the storage library.
- A relation record is data, not an executable instruction.

## 4. M1296 compatibility contract

M1296 shares the same 36 M36 indices but has a different address space:

- Capacity: `36 * 36 = 1296`.
- An edge is `source -> target`; direction is significant.
- `(i,j)` and `(j,i)` are independent slots.
- Edge types: `influence | data_flow | control_flow | dependency_flow | resource_flow | feedback_flow`.
- Weight and confidence use the same numeric bounds as M666.
- Cycles require policy classification; a cycle is not automatically unsafe.

**No implicit conversion:** an M666 symmetric relation must never create, delete, activate or modify an M1296 edge. A proposed directed edge is a separate record with its own direction, type, evidence and approval. Cross-references between the two models are informational only until an explicit, reviewed contract is introduced.

## 5. 36OS runtime API

| Operation | Contract |
|---|---|
| Read protected root | `GET /v1/genome/root`, scope `genome:read` |
| Read M666 registry | `GET /v1/genome/m666`, scope `genome:read` |
| Read M1296 registry | `GET /v1/genome/m1296`, scope `genome:read` |
| Submit proposal | `POST /v1/genome/proposals`, scope `genome:propose` |

M666 read response:

```json
{
  "standard": "M666",
  "version": "1.0.0",
  "capacity": 666,
  "active_count": 0,
  "relations": []
}
```

M1296 read response:

```json
{
  "standard": "M1296",
  "version": "1.0.0",
  "node_count": 36,
  "capacity": 1296,
  "active_count": 0,
  "edges": [],
  "cyclic_components": []
}
```

M666 proposal request:

```json
{
  "proposal_id": "GP-20261128-001",
  "proposal_type": "m666_relation",
  "payload": {
    "gene_a": 0,
    "gene_b": 1,
    "relation_type": "synergy",
    "weight": 0.7,
    "confidence": 0.9
  },
  "rationale": "Evidence-backed rationale with at least twenty characters.",
  "evidence_refs": ["EV-001"],
  "change_level": "L1"
}
```

The proposal envelope is validated by 36OS. Successful submission is only a ledger append and returns `status=proposed`, `requires_human_approval=true`, and `execution_authorized=false`. A successful HTTP response is not evidence that the relation is active.

## 6. Security and governance invariants

1. Default deny; authenticate a trusted service identity on every protected call.
2. Read and proposal scopes are separate; least privilege applies.
3. No database URL, service-role key, bearer token or other secret is stored in this repository or sent to CIE clients.
4. Proposal writes go only through the 36OS API and are audited by 36OS.
5. The proposal ledger is append-only. No consumer may update or delete proposals directly.
6. No proposal is approved, released, executed or merged by M666.
7. M36 root mutation remains human-approval-only. Dynamic code execution is outside this contract.
8. Git JSON registries are versioned source/seed records; they are not a transactional substitute for the 36OS runtime database.

## 7. Compatibility and release gates

A consumer may treat the integration as contract-compatible only when all of the following pass:

- M36 root response resolves to 36 stable, ordered gene IDs and a pinned genome version.
- M666 response declares version 1.0.0, capacity 666, unique canonical slots and a matching active count.
- M1296 response declares version 1.0.0, 36 nodes, capacity 1296 and valid directed edges.
- Both registries use the same pinned M36 index mapping.
- M666 reverse lookup is symmetric; M1296 reverse lookup remains independent.
- Proposal validation rejects malformed IDs, non-canonical indices, invalid relation types, out-of-range weights/confidence and malformed evidence metadata.
- Authenticated API tests prove scope enforcement and the proposal-only lifecycle.
- End-to-end Preview verification confirms audit persistence and append-only behavior.

Current status: **contract specified and client-side validators implemented in this repository; live 36OS Preview authentication, database persistence and end-to-end acceptance remain unverified.** The 36OS standards registry currently labels M666 and M1296 as `implemented_unverified`; this document does not upgrade that status.
