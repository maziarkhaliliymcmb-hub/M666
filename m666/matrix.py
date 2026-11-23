from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

GENE_COUNT = 36
SLOT_COUNT = GENE_COUNT * (GENE_COUNT + 1) // 2  # 666

class RelationType(str, Enum):
    SYNERGY = "synergy"
    DEPENDENCY = "dependency"
    CONFLICT = "conflict"
    INHIBITION = "inhibition"
    REGULATION = "regulation"
    COMPLEMENTARITY = "complementarity"
    NEUTRAL = "neutral"

@dataclass(frozen=True)
class Relation:
    gene_a: int
    gene_b: int
    relation_type: RelationType
    weight: float
    confidence: float
    status: str = "proposed"

    def __post_init__(self):
        if not (0 <= self.gene_a < GENE_COUNT and 0 <= self.gene_b < GENE_COUNT):
            raise ValueError("gene indices must be in [0, 35]")
        if not (-1.0 <= self.weight <= 1.0):
            raise ValueError("weight must be between -1 and 1")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0 and 1")
        if self.gene_a > self.gene_b:
            raise ValueError("relations must use canonical ordering gene_a <= gene_b")

def slot_index(a: int, b: int) -> int:
    if not (0 <= a < GENE_COUNT and 0 <= b < GENE_COUNT):
        raise ValueError("gene indices must be in [0, 35]")
    i, j = sorted((a, b))
    return i * GENE_COUNT - i * (i - 1) // 2 + (j - i)

class M666Matrix:
    """Sparse symmetric upper-triangle address space, including 36 diagonal slots."""
    def __init__(self):
        self._relations: dict[int, Relation] = {}

    @property
    def capacity(self) -> int:
        return SLOT_COUNT

    @property
    def active_count(self) -> int:
        return len(self._relations)

    def set(self, relation: Relation) -> None:
        key = slot_index(relation.gene_a, relation.gene_b)
        self._relations[key] = relation

    def get(self, a: int, b: int) -> Relation | None:
        key = slot_index(a, b)
        return self._relations.get(key)

    def remove(self, a: int, b: int) -> bool:
        return self._relations.pop(slot_index(a, b), None) is not None

    def items(self) -> tuple[Relation, ...]:
        return tuple(self._relations[k] for k in sorted(self._relations))

    def validate(self) -> None:
        if len(self._relations) > SLOT_COUNT:
            raise ValueError("M666 capacity exceeded")
        for key, relation in self._relations.items():
            if key != slot_index(relation.gene_a, relation.gene_b):
                raise ValueError("relation stored at a non-canonical slot")
