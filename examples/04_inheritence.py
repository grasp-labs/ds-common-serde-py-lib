"""
**File:** ``04_inheritence.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Example of inheritance with ``Serializable``.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from ds_common_serde_py_lib import Serializable


class Color(Enum):
    """Example enum to demonstrate enum serialization/deserialization."""

    RED = "red"
    BLUE = "blue"


@dataclass
class BaseProperties(Serializable):
    """Base properties."""

    age: int


@dataclass
class Child(BaseProperties):
    """A nested model used by Parent."""

    count: int


@dataclass
class Parent(BaseProperties):
    """Model demonstrating nested dataclasses and common JSON-compatible types."""

    name: str
    child: Child
    created_at: datetime
    uid: UUID
    color: Color
    values: list[int]
    mapping: dict[str, int]
    optional_note: str | None = None


def main() -> None:
    """
    Run a small round-trip example.

    Returns:
        None
    """
    created_at = datetime(2024, 1, 1, 12, 0, 0)
    uid = uuid4()

    parent = Parent(
        name="parent",
        child=Child(count=3, age=10),
        age=43,
        created_at=created_at,
        uid=uid,
        color=Color.RED,
        values=[1, 2],
        mapping={"one": 1},
        optional_note=None,
    )

    payload = parent.serialize()
    round_tripped = Parent.deserialize(payload)

    assert round_tripped.child.count == 3
    assert round_tripped.child.age == 10
    assert round_tripped.created_at == created_at
    assert round_tripped.uid == uid
    assert round_tripped.color is Color.RED
    assert round_tripped.values == [1, 2]
    assert round_tripped.mapping == {"one": 1}
    assert round_tripped.optional_note is None
    assert round_tripped.age == 43


if __name__ == "__main__":
    main()
