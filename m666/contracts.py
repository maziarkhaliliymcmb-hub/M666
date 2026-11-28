"""Versioned interoperability contracts for M36, M666, M1296 and 36OS.

This module validates the public 36OS genome API payloads. It deliberately does
not perform network access, database access, approvals, or runtime mutations.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .matrix import GENE_COUNT, SLOT_COUNT, M666Matrix, Relation, RelationType

M36_STANDARD = "M36"
M36_ROOT_ID = "M36-ROOT"
M666_STANDARD = "M666"
M666_VERSION = "1.0.0"
M1296_STANDARD = "M1296"
M1296_VERSION = "1.0.0"
M1296_CAPACITY = GENE_COUNT * GENE_COUNT
PROPOSAL_PATH = "/v1/genome/proposals"
M666_READ_PATH = "/v1/genome/m666"
M1296_READ_PATH = "/v1/genome/m1296"
READ_SCOPE = "genome:read"
PROPOSE_SCOPE = "genome:propose"
PROPOSAL_ID_PATTERN = re.compile(r"^GP-[0-9]{8}-[0-9]{3,}$")
M1296_EDGE_TYPES = {
    "influence", "data_flow", "control_flow", "dependency_flow",
    "resource_flow", "feedback_flow",
}


class ContractError(ValueError):
    """Raised when an API payload violates the versioned genome contract."""


@dataclass(frozen=True)
class M36GeneIndex:
    """Immutable 0-based index derived from the ordered M36 root genome."""

    genome_id: str
    genome_version: str
    gene_ids: tuple[str, ...]

    @classmethod
    def from_root_response(cls, response: Mapping[str, Any]) -> "M36GeneIndex":
        if response.get("standard") != M36_STANDARD:
            raise ContractError("root response standard must be M36")
        if response.get("gene_count") != GENE_COUNT:
            raise ContractError("M36 root must expose exactly 36 genes")
        genome = response.get("genome")
        if not isinstance(genome, Mapping):
            raise ContractError("M36 root response must contain a genome object")
        if genome.get("standard") != M36_STANDARD:
            raise ContractError("embedded genome standard must be M36")
        if genome.get("genome_id") != M36_ROOT_ID:
            raise ContractError("M36 root genome_id must be M36-ROOT")
        if response.get("root_protected") is not True:
            raise ContractError("M36 root response must confirm root_protected=true")
        governance = genome.get("governance")
        if not isinstance(governance, Mapping) or governance.get("root_protected") is not True:
            raise ContractError("M36 root genome must be constitutionally protected")
        if governance.get("root_modification") != "approval_required":
            raise ContractError("M36 root mutation must require approval")
        genome_version = genome.get("genome_version")
        if not isinstance(genome_version, str) or not genome_version:
            raise ContractError("M36 genome_version is required")
        structure = genome.get("structure")
        if structure != {
            "chromosomes": 6,
            "genes_per_chromosome": 6,
            "total_genes": GENE_COUNT,
        }:
            raise ContractError("M36 structure must be exactly 6x6=36")
        chromosomes = genome.get("chromosomes")
        if not isinstance(chromosomes, list) or len(chromosomes) != 6:
            raise ContractError("M36 must contain six ordered chromosomes")

        gene_ids: list[str] = []
        for chromosome_index, chromosome in enumerate(chromosomes, start=1):
            if not isinstance(chromosome, Mapping) or chromosome.get("index") != chromosome_index:
                raise ContractError("M36 chromosome order must be 1..6")
            genes = chromosome.get("genes")
            if not isinstance(genes, list) or len(genes) != 6:
                raise ContractError("each M36 chromosome must contain six genes")
            for gene_index, gene in enumerate(genes, start=1):
                if not isinstance(gene, Mapping):
                    raise ContractError("M36 gene entries must be objects")
                expected = f"M36-CHR{chromosome_index:02d}-G{gene_index:02d}"
                if gene.get("id") != expected:
                    raise ContractError(f"expected stable M36 gene id {expected}")
                gene_ids.append(expected)

        if len(set(gene_ids)) != GENE_COUNT:
            raise ContractError("M36 gene identifiers must be unique")
        return cls(
            genome_id=M36_ROOT_ID,
            genome_version=genome_version,
            gene_ids=tuple(gene_ids),
        )

    def index_of(self, gene_id: str) -> int:
        try:
            return self.gene_ids.index(gene_id)
        except ValueError as exc:
            raise ContractError(f"unknown M36 gene id: {gene_id}") from exc

    def gene_id_at(self, index: int) -> str:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < GENE_COUNT:
            raise ContractError("gene index must be an integer in [0, 35]")
        return self.gene_ids[index]

    def relation(
        self,
        gene_a_id: str,
        gene_b_id: str,
        relation_type: RelationType | str,
        weight: float,
        confidence: float,
        status: str = "proposed",
    ) -> Relation:
        """Create a canonical M666 relation from stable M36 gene identifiers."""
        a, b = sorted((self.index_of(gene_a_id), self.index_of(gene_b_id)))
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ContractError("weight must be numeric")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ContractError("confidence must be numeric")
        if not isinstance(status, str) or not status:
            raise ContractError("status must be a non-empty string")
        try:
            kind = relation_type if isinstance(relation_type, RelationType) else RelationType(relation_type)
            return Relation(a, b, kind, weight, confidence, status)
        except (TypeError, ValueError) as exc:
            raise ContractError(str(exc)) from exc


@dataclass(frozen=True)
class M666RegistrySnapshot:
    version: str
    capacity: int
    relations: tuple[Relation, ...]


def parse_m666_registry(response: Mapping[str, Any]) -> M666RegistrySnapshot:
    """Validate GET /v1/genome/m666 response against the 36OS API contract."""
    if response.get("standard") != M666_STANDARD:
        raise ContractError("registry standard must be M666")
    version = response.get("version")
    if version != M666_VERSION:
        raise ContractError(f"unsupported M666 registry version: {version!r}")
    if response.get("capacity") != SLOT_COUNT:
        raise ContractError("M666 capacity must be 666")
    raw_relations = response.get("relations")
    if not isinstance(raw_relations, list):
        raise ContractError("M666 relations must be an array")

    matrix = M666Matrix()
    seen: set[int] = set()
    for raw in raw_relations:
        if not isinstance(raw, Mapping):
            raise ContractError("M666 relation entries must be objects")
        try:
            for field in ("gene_a", "gene_b"):
                if isinstance(raw[field], bool) or not isinstance(raw[field], int):
                    raise ContractError(f"{field} must be an integer M36 index")
            for field in ("weight", "confidence"):
                if isinstance(raw[field], bool) or not isinstance(raw[field], (int, float)):
                    raise ContractError(f"{field} must be numeric")
            if not isinstance(raw.get("status", "active"), str) or not raw.get("status", "active"):
                raise ContractError("status must be a non-empty string")
            relation = Relation(
                gene_a=raw["gene_a"],
                gene_b=raw["gene_b"],
                relation_type=RelationType(raw["relation_type"]),
                weight=raw["weight"],
                confidence=raw["confidence"],
                status=raw.get("status", "active"),
            )
            from .matrix import slot_index
            slot = slot_index(relation.gene_a, relation.gene_b)
            if slot in seen:
                raise ContractError("duplicate canonical M666 relation slot")
            seen.add(slot)
            matrix.set(relation)
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ContractError):
                raise
            raise ContractError(f"invalid M666 relation: {exc}") from exc

    matrix.validate()
    active_count = response.get("active_count")
    if isinstance(active_count, bool) or active_count != len(raw_relations):
        raise ContractError("active_count must equal the number of returned relations")
    return M666RegistrySnapshot(
        version=version,
        capacity=SLOT_COUNT,
        relations=matrix.items(),
    )


def validate_m1296_registry(response: Mapping[str, Any], gene_index: M36GeneIndex) -> None:
    """Validate M1296's shared 36-node address space without importing its runtime."""
    if response.get("standard") != M1296_STANDARD:
        raise ContractError("companion registry standard must be M1296")
    if response.get("version") != M1296_VERSION:
        raise ContractError("unsupported M1296 registry version")
    if response.get("node_count") != len(gene_index.gene_ids):
        raise ContractError("M1296 node_count must match the M36 gene count")
    if response.get("capacity") != M1296_CAPACITY:
        raise ContractError("M1296 capacity must be 1296")
    edges = response.get("edges")
    if not isinstance(edges, list):
        raise ContractError("M1296 edges must be an array")
    active_count = response.get("active_count")
    if isinstance(active_count, bool) or not isinstance(active_count, int) or not 0 <= active_count <= len(edges):
        raise ContractError("M1296 active_count is invalid")
    seen_slots: set[tuple[int, int]] = set()
    observed_active = 0
    for edge in edges:
        if not isinstance(edge, Mapping):
            raise ContractError("M1296 edge entries must be objects")
        source, target = edge.get("source"), edge.get("target")
        if any(isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < GENE_COUNT for x in (source, target)):
            raise ContractError("M1296 source and target must be M36 indices in [0, 35]")
        if (source, target) in seen_slots:
            raise ContractError("duplicate directed M1296 edge slot")
        seen_slots.add((source, target))
        if edge.get("edge_type") not in M1296_EDGE_TYPES:
            raise ContractError("unsupported M1296 edge_type")
        active = edge.get("active", True)
        if not isinstance(active, bool):
            raise ContractError("M1296 active must be boolean")
        observed_active += int(active)
        for field in ("weight", "confidence"):
            value = edge.get(field, 1.0)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ContractError(f"M1296 {field} must be numeric")
            if field == "weight" and not -1.0 <= value <= 1.0:
                raise ContractError("M1296 weight must be in [-1, 1]")
            if field == "confidence" and not 0.0 <= value <= 1.0:
                raise ContractError("M1296 confidence must be in [0, 1]")
    if active_count != observed_active:
        raise ContractError("M1296 active_count must equal the number of active edges")


def build_m666_proposal(
    proposal_id: str,
    relation: Relation,
    rationale: str,
    evidence_refs: Sequence[str] = (),
    change_level: str = "L1",
) -> dict[str, Any]:
    """Build the exact POST /v1/genome/proposals envelope accepted by 36OS."""
    if not isinstance(proposal_id, str) or not PROPOSAL_ID_PATTERN.fullmatch(proposal_id):
        raise ContractError("proposal_id must match GP-YYYYMMDD-NNN")
    if not isinstance(rationale, str) or len(rationale) < 20 or len(rationale) > 8000:
        raise ContractError("rationale must contain 20..8000 characters")
    if not isinstance(change_level, str) or change_level not in {"L1", "L2", "L3"}:
        raise ContractError("change_level must be L1, L2 or L3")
    if isinstance(evidence_refs, (str, bytes)) or not isinstance(evidence_refs, Sequence):
        raise ContractError("evidence_refs must be a sequence of strings")
    if len(evidence_refs) > 50 or any(not isinstance(ref, str) or not ref for ref in evidence_refs):
        raise ContractError("evidence_refs must contain at most 50 non-empty strings")
    return {
        "proposal_id": proposal_id,
        "proposal_type": "m666_relation",
        "payload": {
            "gene_a": relation.gene_a,
            "gene_b": relation.gene_b,
            "relation_type": relation.relation_type.value,
            "weight": relation.weight,
            "confidence": relation.confidence,
        },
        "rationale": rationale,
        "evidence_refs": list(evidence_refs),
        "change_level": change_level,
    }
