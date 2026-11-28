import pytest

from m666.contracts import (
    ContractError,
    CORE_INTEROPERABILITY_CONTRACT_VERSION,
    M36GeneIndex,
    build_m666_proposal,
    parse_m666_registry,
    validate_m1296_registry,
)
from m666.matrix import RelationType


def root_response():
    chromosomes = []
    for chromosome_index in range(1, 7):
        chromosomes.append({
            "index": chromosome_index,
            "genes": [
                {"id": f"M36-CHR{chromosome_index:02d}-G{gene_index:02d}"}
                for gene_index in range(1, 7)
            ],
        })
    return {
        "standard": "M36",
        "gene_count": 36,
        "root_protected": True,
        "genome": {
            "standard": "M36",
            "genome_id": "M36-ROOT",
            "standard_version": "1.0.0",
            "genome_version": "1.0.0",
            "governance": {
                "root_protected": True,
                "root_modification": "approval_required",
            },
            "structure": {
                "chromosomes": 6,
                "genes_per_chromosome": 6,
                "total_genes": 36,
            },
            "chromosomes": chromosomes,
        },
    }


def test_m36_index_is_stable_and_zero_based():
    index = M36GeneIndex.from_root_response(root_response())
    assert index.gene_id_at(0) == "M36-CHR01-G01"
    assert index.gene_id_at(35) == "M36-CHR06-G06"
    assert index.index_of("M36-CHR02-G01") == 6
    assert index.genome_id == "M36-ROOT"
    assert index.root_schema_version == "1.0.0"
    assert index.genome_version == "1.0.0"


def test_m36_index_rejects_bad_root_or_gene_order():
    response = root_response()
    response["gene_count"] = 35
    with pytest.raises(ContractError):
        M36GeneIndex.from_root_response(response)

    response = root_response()
    response["genome"]["chromosomes"][0]["genes"][0]["id"] = "unstable-id"
    with pytest.raises(ContractError):
        M36GeneIndex.from_root_response(response)

    response = root_response()
    response["root_protected"] = False
    with pytest.raises(ContractError):
        M36GeneIndex.from_root_response(response)


def test_relation_from_stable_ids_canonicalizes_pair():
    index = M36GeneIndex.from_root_response(root_response())
    relation = index.relation(
        "M36-CHR02-G01",
        "M36-CHR01-G01",
        RelationType.SYNERGY,
        0.7,
        0.9,
    )
    assert (relation.gene_a, relation.gene_b) == (0, 6)


def test_m666_registry_contract_and_sparse_semantics():
    snapshot = parse_m666_registry({
        "standard": "M666",
        "version": "1.0.0",
        "capacity": 666,
        "active_count": 1,
        "relations": [{
            "gene_a": 0,
            "gene_b": 6,
            "relation_type": "synergy",
            "weight": 0.7,
            "confidence": 0.9,
            "status": "active",
        }],
    })
    assert snapshot.capacity == 666
    assert len(snapshot.relations) == 1
    assert snapshot.relations[0].gene_a == 0


def test_m666_registry_rejects_boolean_indices_and_non_numeric_weights():
    with pytest.raises(ContractError):
        parse_m666_registry({
            "standard": "M666",
            "version": "1.0.0",
            "capacity": 666,
            "active_count": 1,
            "relations": [{
                "gene_a": True,
                "gene_b": 2,
                "relation_type": "synergy",
                "weight": 0.7,
                "confidence": 0.9,
            }],
        })


def test_m666_registry_rejects_noncanonical_duplicate_and_count_mismatch():
    base = {
        "standard": "M666",
        "version": "1.0.0",
        "capacity": 666,
        "active_count": 1,
        "relations": [{
            "gene_a": 6,
            "gene_b": 0,
            "relation_type": "synergy",
            "weight": 0.7,
            "confidence": 0.9,
        }],
    }
    with pytest.raises(ContractError):
        parse_m666_registry(base)

    base["relations"] = [
        {"gene_a": 0, "gene_b": 6, "relation_type": "synergy", "weight": 0.7, "confidence": 0.9},
        {"gene_a": 0, "gene_b": 6, "relation_type": "conflict", "weight": -0.2, "confidence": 0.8},
    ]
    base["active_count"] = 2
    with pytest.raises(ContractError):
        parse_m666_registry(base)

    base["relations"] = []
    base["active_count"] = 1
    with pytest.raises(ContractError):
        parse_m666_registry(base)


def test_m1296_contract_shares_m36_address_space_but_keeps_direction():
    index = M36GeneIndex.from_root_response(root_response())
    response = {
        "standard": "M1296",
        "version": "1.0.0",
        "root_schema_version": index.root_schema_version,
        "root_genome_version": index.genome_version,
        "node_count": 36,
        "capacity": 1296,
        "active_count": 2,
        "edges": [
            {"source": 0, "target": 6, "edge_type": "influence", "weight": 0.5, "confidence": 0.9, "active": True},
            {"source": 6, "target": 0, "edge_type": "influence", "weight": -0.1, "confidence": 0.7, "active": True},
        ],
        "cyclic_components": [],
    }
    validate_m1296_registry(response, index)
    response.pop("root_schema_version")
    with pytest.raises(ContractError):
        validate_m1296_registry(response, index)
    response["root_schema_version"] = "2.0.0"
    with pytest.raises(ContractError):
        validate_m1296_registry(response, index)
    response["root_schema_version"] = index.root_schema_version
    response["root_genome_version"] = "0.9.0"
    with pytest.raises(ContractError):
        validate_m1296_registry(response, index)
    response["root_genome_version"] = index.genome_version
    response["node_count"] = 35
    with pytest.raises(ContractError):
        validate_m1296_registry(response, index)

    response["node_count"] = 36
    response["active_count"] = 1
    with pytest.raises(ContractError):
        validate_m1296_registry(response, index)

    response["active_count"] = 2
    response["edges"].append(dict(response["edges"][0]))
    with pytest.raises(ContractError):
        validate_m1296_registry(response, index)


def test_proposal_envelope_matches_36os_api_and_is_non_executable():
    index = M36GeneIndex.from_root_response(root_response())
    relation = index.relation(
        "M36-CHR01-G01",
        "M36-CHR01-G02",
        "synergy",
        0.4,
        0.85,
    )
    proposal = build_m666_proposal(
        "GP-20261128-001",
        relation,
        "Observed co-activation in two independently validated test runs.",
        ["EV-001"],
    )
    assert proposal["proposal_type"] == "m666_relation"
    assert proposal["payload"]["gene_a"] == 0
    assert proposal["payload"]["gene_b"] == 1
    assert proposal["change_level"] == "L1"
    assert "execution_authorized" not in proposal


def test_proposal_builder_rejects_invalid_envelope():
    index = M36GeneIndex.from_root_response(root_response())
    relation = index.relation(
        "M36-CHR01-G01",
        "M36-CHR01-G02",
        "synergy",
        0.4,
        0.85,
    )
    with pytest.raises(ContractError):
        build_m666_proposal("bad-id", relation, "This rationale is long enough.")
    with pytest.raises(ContractError):
        build_m666_proposal("GP-20261128-002", relation, "too short")
    with pytest.raises(ContractError):
        build_m666_proposal(
            "GP-20261128-003",
            relation,
            "This rationale is long enough for validation.",
            change_level="L5",
        )

def test_contracts_reject_float_valued_counts_and_indices():
    response = root_response()
    response["gene_count"] = 36.0
    with pytest.raises(ContractError):
        M36GeneIndex.from_root_response(response)

    response = root_response()
    response["genome"]["structure"]["chromosomes"] = 6.0
    with pytest.raises(ContractError):
        M36GeneIndex.from_root_response(response)

    response = root_response()
    response["genome"]["chromosomes"][0]["index"] = 1.0
    with pytest.raises(ContractError):
        M36GeneIndex.from_root_response(response)

    m666 = {
        "standard": "M666", "version": "1.0.0", "capacity": 666.0,
        "active_count": 0, "relations": [],
    }
    with pytest.raises(ContractError):
        parse_m666_registry(m666)

    m666["capacity"] = 666
    m666["active_count"] = 0.0
    with pytest.raises(ContractError):
        parse_m666_registry(m666)

    index = M36GeneIndex.from_root_response(root_response())
    m1296 = {
        "standard": "M1296", "version": "1.0.0", "node_count": 36.0,
        "capacity": 1296, "active_count": 0, "edges": [],
    }
    with pytest.raises(ContractError):
        validate_m1296_registry(m1296, index)

    m1296["node_count"] = 36
    m1296["capacity"] = 1296.0
    with pytest.raises(ContractError):
        validate_m1296_registry(m1296, index)



@pytest.mark.parametrize("bad_schema_version", [None, "", "2.0.0", "not-semver"])
def test_m36_index_rejects_missing_or_unsupported_root_schema_version(bad_schema_version):
    response = root_response()
    if bad_schema_version is None:
        response["genome"].pop("standard_version")
    else:
        response["genome"]["standard_version"] = bad_schema_version
    with pytest.raises(ContractError, match="root schema"):
        M36GeneIndex.from_root_response(response)



def test_m666_uses_core_interoperability_contract_1_1_0():
    assert CORE_INTEROPERABILITY_CONTRACT_VERSION == "1.1.0"
