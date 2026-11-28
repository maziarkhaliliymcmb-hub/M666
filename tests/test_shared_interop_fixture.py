import json
from pathlib import Path

from m666.contracts import (
    M36GeneIndex,
    parse_m666_registry,
    validate_m1296_registry,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/core-interoperability-v1.1.0.json"


def test_shared_fixture_passes_m666_and_m1296_consumer_contracts():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    index = M36GeneIndex.from_root_response(fixture["root_response"])
    m666 = parse_m666_registry(fixture["m666_response"])
    validate_m1296_registry(fixture["m1296_response"], index)

    assert index.root_schema_version == "1.0.0"
    assert index.genome_version == "1.0.0"
    assert len(index.gene_ids) == 36
    assert m666.capacity == 666
    assert m666.relations == ()


def test_shared_fixture_keeps_m666_and_m1296_root_version_pins_equal():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    root = fixture["root_response"]["genome"]
    for key in ("m666_response", "m1296_response"):
        assert fixture[key]["root_schema_version"] == root["standard_version"]
        assert fixture[key]["root_genome_version"] == root["genome_version"]
