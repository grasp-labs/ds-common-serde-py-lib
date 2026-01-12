"""
**File:** ``02_custom_deserializers.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Override per-field conversion using ``__deserializers__``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ds_common_serde_py_lib import Serializable


@dataclass
class Address(Serializable):
    """Model representing a physical address."""

    street: str
    city: str
    state: str
    zip: str


@dataclass
class CustomModel(Serializable):
    """Model showing per-field custom conversion logic."""

    __deserializers__: ClassVar[dict[str, Any]] = {"name": lambda value: value.title()}

    name: str
    amount: int
    address: Address


def main() -> None:
    """Run a small custom deserializer example."""
    data = {
        "name": "john doe",
        "amount": "7",
        "address": {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "12345",
        },
    }

    model = CustomModel.deserialize(data)
    print(model)

    assert model.name == "John Doe"
    assert model.amount == 7
    assert model.address.street == "123 Main St"
    assert model.address.city == "Anytown"
    assert model.address.state == "CA"
    assert model.address.zip == "12345"


if __name__ == "__main__":
    main()
