import pytest
from m666.matrix import M666Matrix, Relation, RelationType, slot_index, SLOT_COUNT

def test_address_space_has_666_unique_slots():
    slots = {slot_index(i, j) for i in range(36) for j in range(i, 36)}
    assert len(slots) == SLOT_COUNT == 666
    assert min(slots) == 0 and max(slots) == 665

def test_symmetric_lookup_uses_one_canonical_relation():
    matrix = M666Matrix()
    relation = Relation(2, 9, RelationType.SYNERGY, 0.7, 0.9)
    matrix.set(relation)
    assert matrix.get(2, 9) == matrix.get(9, 2)
    assert matrix.active_count == 1

def test_rejects_noncanonical_and_invalid_values():
    with pytest.raises(ValueError):
        Relation(9, 2, RelationType.CONFLICT, -0.4, 0.8)
    with pytest.raises(ValueError):
        Relation(1, 2, RelationType.SYNERGY, 2.0, 0.5)

def test_sparse_matrix_capacity_and_remove():
    matrix = M666Matrix()
    matrix.set(Relation(0, 0, RelationType.REGULATION, 0.1, 1.0))
    assert matrix.remove(0, 0)
    assert matrix.active_count == 0
