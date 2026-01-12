"""
**File:** ``05_error_handling.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Examples of explicit failure handling for ``Serializable.serialize()`` and
``Serializable.deserialize()``.

This script intentionally triggers failures and asserts that the library raises
structured exceptions:
- ``SerializationError`` for serialization failures
- ``DeserializationError`` for deserialization failures
"""

from __future__ import annotations

from dataclasses import dataclass

from ds_common_serde_py_lib import Serializable
from ds_common_serde_py_lib.errors import DeserializationError, SerializationError


def serialize_failure_example() -> None:
    """Demonstrate a serialization failure and inspect structured details."""

    class PlainSerializable(Serializable):
        """Not a dataclass on purpose."""

        pass

    try:
        plain_serializable = PlainSerializable()
        plain_serializable.serialize()
        raise AssertionError("Expected SerializationError to be raised")
    except SerializationError as exc:
        assert exc.code == "DS_SERIALIZATION_ERROR"
        assert exc.status_code == 500
        assert exc.message == "Serialization did not produce an object"
        assert exc.details.get("class_name") == "PlainSerializable"


def deserialize_failure_example() -> None:
    """Demonstrate a deserialization failure and inspect structured details."""

    @dataclass
    class Model(Serializable):
        count: int

    try:
        # `count` is expected to be an int; this cannot be converted.
        Model.deserialize({"count": "not-an-int"})
        raise AssertionError("Expected DeserializationError to be raised")
    except DeserializationError as exc:
        assert exc.code == "DS_DESERIALIZATION_ERROR"
        assert exc.status_code == 500
        assert exc.message  # non-empty
        assert exc.details.get("class_name") == "Model"
        assert exc.message == "invalid literal for int() with base 10: 'not-an-int'"
        # Best-effort context (may be None depending on where conversion fails)
        assert "error_type" in exc.details


def main() -> None:
    """Run both failure examples."""

    serialize_failure_example()
    deserialize_failure_example()


if __name__ == "__main__":
    main()
