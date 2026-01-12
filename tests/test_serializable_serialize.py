"""
**File:** ``test_serializable_serialize.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Tests for ``_serializable_serialize`` (``_serialize_value``).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import uuid4

from ds_common_serde_py_lib.serializable import Serializable, _serialize_value


class Color(Enum):
    RED = "red"


@dataclass
class Child(Serializable):
    count: int


def test_serialize_value_handles_enum_uuid_datetime_and_dataclass():
    """Test that the _serialize_value function handles enums, UUIDs, datetimes, and dataclasses."""
    uid = uuid4()
    timestamp = datetime(2025, 1, 1, 12, 0, 0)

    assert _serialize_value(Color.RED) == "red"
    assert _serialize_value(uid) == str(uid)
    assert _serialize_value(timestamp) == timestamp.isoformat()
    assert _serialize_value(Child(count=3)) == {"count": 3}


def test_serialize_value_falls_back_when_object_serialize_raises():
    """Test that the _serialize_value function falls back when an object's serialize method raises an error."""

    class RaisesSerialize:
        def serialize(self):
            raise RuntimeError("boom")

    obj = RaisesSerialize()
    assert _serialize_value(obj) is obj
