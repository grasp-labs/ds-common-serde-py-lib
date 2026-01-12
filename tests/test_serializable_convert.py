"""
**File:** ``test_serializable_convert.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Tests for ``_serializable_convert`` (``_convert_value``).
"""

from __future__ import annotations

import builtins
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import ForwardRef, Generic, TypeVar
from uuid import UUID

import pytest

from ds_common_serde_py_lib import _serializable_convert
from ds_common_serde_py_lib._serializable_convert import _convert_value
from ds_common_serde_py_lib.serializable import Serializable


class Color(Enum):
    RED = "red"


@dataclass
class Child(Serializable):
    count: int


def test_convert_value_iterables_and_mappings():
    """Test that the _convert_value function converts iterables and mappings to the correct types."""
    assert _convert_value(["1", "2"], list[int]) == [1, 2]
    assert _convert_value(("1", "2"), tuple[int, int]) == (1, 2)
    assert _convert_value({"a": "3"}, dict[str, int]) == {"a": 3}
    assert _convert_value({"x", "y"}, set[str]) == {"x", "y"}
    assert _convert_value((1, "2"), Iterable[int]) == [1, 2]
    assert _convert_value(None, int | None) is None


def test_convert_value_datetime():
    """Test that the _convert_value function converts a datetime string to a datetime object."""
    iso_value = "2024-03-01T00:00:00"
    assert _convert_value(iso_value, datetime) == datetime.fromisoformat(iso_value)

    now = datetime.now()
    assert _convert_value(now, datetime) is now

    with pytest.raises(ValueError):
        _convert_value(["not", "valid"], datetime)


def test_convert_value_union():
    """Test that the _convert_value function converts a union type."""
    assert _convert_value(None, int | None) is None
    assert _convert_value(None, str | int | None) is None
    assert _convert_value("5", int | UUID) == 5

    with pytest.raises(ValueError):
        _convert_value("not-a-uuid", int | UUID)

    with pytest.raises(ValueError):
        _convert_value("abc", int | datetime)


def test_convert_value_returns_existing_instance():
    """Test that the _convert_value function returns an existing instance."""
    child = Child(count=4)
    assert _convert_value(child, Child) is child


def test_convert_value_respects_deserialize_method():
    """Test that the _convert_value function respects the deserialize method."""

    class CustomDeserializable:
        @classmethod
        def deserialize(cls, payload: dict[str, str]) -> str:
            return f"parsed-{payload['raw']}"

    result = _convert_value({"raw": "value"}, CustomDeserializable)
    assert result == "parsed-value"


def test_convert_value_handles_edge_cases():
    """Test that the _convert_value function handles edge cases."""
    assert _convert_value(Color.RED, Color) is Color.RED
    assert _convert_value("x", {"not": "a type"}) == "x"
    assert _convert_value("value", ForwardRef("Example")) == "value"

    with pytest.raises(ValueError):
        _convert_value("not-a-uuid", UUID)


def test_convert_value_mapping_to_class_with_kwargs():
    """Test that the _convert_value function converts a mapping to a class with kwargs."""

    class _WithKwargs:
        def __init__(self, a: int, b: str = "x", **kwargs):
            self.a = a
            self.b = b
            self.extra = kwargs.get("extra")

    result = _convert_value({"a": "1", "b": "y", "extra": 2}, _WithKwargs)
    assert result.a == 1
    assert result.b == "y"
    assert result.extra == 2


def test_convert_value_mapping_falls_back_to_single_arg_constructor():
    """Test that the _convert_value function falls back to a single-argument constructor."""

    class _AcceptsMapping:
        def __init__(self, value):
            self.value = value

    mapping = {"a": 1}
    result = _convert_value(mapping, _AcceptsMapping)
    assert result.value == mapping


def test_is_direct_dataclass_serializable_returns_false_if_import_fails(monkeypatch):
    """Cover the import-failure branch in _is_direct_dataclass_serializable()."""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "ds_common_serde_py_lib.serializable":
            raise ImportError("boom")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert _serializable_convert._is_direct_dataclass_serializable(int) is False


def test_convert_value_falls_back_when_get_type_hints_raises(monkeypatch):
    """Cover the except branch around get_type_hints(type_hint.__init__)."""

    class _WithKwargs:
        def __init__(self, a: int, **kwargs):
            self.a = a
            self.kwargs = kwargs

    monkeypatch.setattr(_serializable_convert, "get_type_hints", lambda *_a, **_k: (_ for _ in ()).throw(Exception("nope")))
    obj = _convert_value({"a": "1"}, _WithKwargs)
    # When get_type_hints fails, we don't know expected arg types, so we should not coerce.
    assert obj.a == "1"


def test_convert_value_uses_mapping_directly_when_signature_unavailable(monkeypatch):
    """Cover the inspect.signature exception path and the `sig is None` kwargs fallback."""

    class _AcceptsAnyKwargs:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(_serializable_convert.inspect, "signature", lambda *_a, **_k: (_ for _ in ()).throw(TypeError("no sig")))
    obj = _convert_value({"x": 1}, _AcceptsAnyKwargs)
    assert obj.kwargs == {"x": 1}


def test_convert_value_optional_continues_past_none_member():
    """Cover the `continue` for the NoneType member in a union when value is not None."""
    # Ensure NoneType is visited before the matching type (arg ordering matters).
    assert _convert_value("5", None | int) == 5


def test_convert_value_uniontype_import_failure_does_not_break_typing_union(monkeypatch):
    """Cover the ImportError branch for importing types.UnionType."""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "types":
            raise ImportError("no types")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert _convert_value("5", int | str) == 5


def test_convert_value_uses_origin_deserialize_for_parametrized_serializable():
    """Cover origin-based deserialization via `typing.get_origin` on parametrized generics."""
    t_val = TypeVar("t_val")

    @dataclass
    class GenericChild(Serializable, Generic[t_val]):
        count: int

    obj = _convert_value({"count": "7"}, GenericChild[int])
    assert obj == GenericChild(count=7)
