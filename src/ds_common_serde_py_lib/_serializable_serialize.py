"""
**File:** ``_serializable_serialize.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Defines internal serialization helpers for ``Serializable.serialize()``,
including recursive conversion of dataclasses and common JSON-compatible types.

Example
-------
.. code-block:: python

    from dataclasses import dataclass

    from ds_common_serde_py_lib import Serializable


    @dataclass
    class Child(Serializable):
        count: int


    assert Child(count=3).serialize() == {"count": 3}
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields as dc_fields
from dataclasses import is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from ds_common_logger_py_lib import Logger

logger = Logger.get_logger(__name__, package=True)


def _serialize_value(value: Any) -> Any:
    """Recursively serialize common Python types and dataclasses.

    Returns a structure comprised of dicts, lists, and primitives that can be
    JSON-encoded without custom hooks.

    Args:
        value: The value to serialize.

    Returns:
        The serialized value.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        result: dict[str, Any] = {}
        for f in dc_fields(value):
            result[f.name] = _serialize_value(getattr(value, f.name))
        return result
    if hasattr(value, "serialize") and callable(value.serialize):
        try:
            return value.serialize()
        except Exception as exc:
            logger.debug("Failed to serialize object %s: %s", type(value).__name__, exc)
    if isinstance(value, Mapping):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(v) for v in value]
    return value
