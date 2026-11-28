from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math

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


def _require_index(value: int, field: str) -> None:
    if type(value) is not int or not 0 <= value < GENE_COUNT:
        raise ValueError(f"{field} must be an integer in [0, 35]")


def _require_finite_number(value: float, field: str, lower: float, upper: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{field} must be a finite number")
    if not lower <= value <= upper:
        raise ValueError(f"{field} must be between {lower} and {upper}")


@dataclass(frozen=True)
class Relation:
    gene_a: int
    gene_b: int
    relation_type: RelationType
    weight: float
    confidence: float
    status: str = "proposed"

    def __post_init__(self):
        _require_index(self.gene_a, "gene_a")
        _require_index(self.gene_b, "gene_b")
        if not isinstance(self.relation_type, RelationType):
            raise ValueError("relation_type must be a RelationType")
        _require_finite_number(self.weight, "weight", -1.0, 1.0)
        _require_finite_number(self.confidence, "confidence", 0.0, 1.0)
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status must be a non-empty string")
        if self.gene_a > self.gene_b:
            raise ValueError("relations must use canonical ordering gene_a <= gene_b")


def slot_index(a: int, b: int) -> int:
    _require_index(a, "gene_a")
    _require_index(b, "gene_b")
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
        if not isinstance(relation, Relation):
            raise TypeError("relation must be a Relation")
        key = slot_index(relation.gene_a, relation.gene_b)
        self._relations[key] = relation

    def get(self, a: int, b: int) -> Relation | None:
        return self._relations.get(slot_index(a, b))

    def remove(self, a: int, b: int) -> bool:
        return self._relations.pop(slot_index(a, b), None) is not None

    def items(self) -> tuple[Relation, ...]:
        return tuple(self._relations[k] for k in sorted(self._relations))

    def validate(self) -> None:
        if len(self._relations) > SLOT_COUNT:
            raise ValueError("M666 capacity exceeded")
        for key, relation in self._relations.items():
            if not isinstance(relation, Relation):
                raise ValueError("matrix contains a non-Relation value")
            if key != slot_index(relation.gene_a, relation.gene_b):
                raise ValueError("relation stored at a non-canonical slot")
