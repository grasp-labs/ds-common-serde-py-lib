"""
**File:** ``03_init_false_fields.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Demonstrate ``init=False`` dataclass fields being set during ``deserialize()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ds_common_serde_py_lib import Serializable


@dataclass
class WithInitFalse(Serializable):
    """Model with fields that are excluded from __init__ but set post-deserialize."""

    name: str
    computed: str = field(init=False, default="computed")
    dynamic: str = field(init=False, default_factory=lambda: "dynamic")


def main() -> None:
    """
    Run a small init=False example.

    Returns:
        None
    """
    instance = WithInitFalse.deserialize({"name": "example"})
    print(instance)

    assert instance.name == "example"
    assert instance.computed == "computed"
    assert instance.dynamic == "dynamic"


if __name__ == "__main__":
    main()
