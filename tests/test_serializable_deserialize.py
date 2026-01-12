"""
**File:** ``test_serializable_deserialize.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Tests for ``_serializable_deserialize`` helpers.
"""

from dataclasses import dataclass, field, fields
from typing import Any, Generic, TypeVar, get_origin

from ds_common_serde_py_lib._serializable_deserialize import (
    TypeVarType,
    _build_type_var_map,
    _get_class_type_hints,
    _resolve_type_hint_for_field,
    _set_init_false_fields,
)
from ds_common_serde_py_lib.serializable import Serializable


def test_build_type_var_map_handles_exception_on_parameters(monkeypatch):
    """Test that the _build_type_var_map function handles an exception on parameters."""
    T = TypeVar("T")

    @dataclass
    class TestClass(Serializable, Generic[T]):
        value: T  # type: ignore[type-arg]

    class FailingOrigin:
        def __getattribute__(self, name):
            if name == "__parameters__":
                raise RuntimeError("Cannot access __parameters__")
            return super().__getattribute__(name)

    original_get_origin = get_origin

    def mock_get_origin(base_alias):
        result = original_get_origin(base_alias)
        if result is not None:
            return FailingOrigin()
        return result

    monkeypatch.setattr("typing.get_origin", mock_get_origin, raising=False)
    result = _build_type_var_map(TestClass)
    assert isinstance(result, dict)


def test_resolve_type_hint_uses_cls_own_hints_when_field_type_is_any():
    """Test that the _resolve_type_hint_for_field function uses the class own hints when the field type is Any."""

    @dataclass
    class TestClass(Serializable):
        value: Any

    field_obj = fields(TestClass)[0]
    cls_own_hints = {"value": int}
    type_var_map: dict[Any, Any] = {}

    original_type = field_obj.type
    field_obj.type = None

    hint = _resolve_type_hint_for_field(
        field=field_obj,
        field_name="value",
        cls_own_hints=cls_own_hints,
        type_var_map=type_var_map,
        cls=TestClass,
    )

    assert isinstance(hint, type) and hint is int
    field_obj.type = original_type


def test_resolve_type_hint_successfully_resolves_string_annotation():
    """Test that the _resolve_type_hint_for_field function successfully resolves a string annotation."""

    @dataclass
    class TestClass(Serializable):
        value: "int"

    field_obj = fields(TestClass)[0]
    original_type = field_obj.type
    field_obj.type = "int"
    cls_own_hints: dict[str, Any] = {}
    type_var_map: dict[Any, Any] = {}

    hint = _resolve_type_hint_for_field(
        field=field_obj,
        field_name="value",
        cls_own_hints=cls_own_hints,
        type_var_map=type_var_map,
        cls=TestClass,
    )

    assert (isinstance(hint, type) and hint is int) or isinstance(hint, str)
    field_obj.type = original_type


def test_set_init_false_fields_with_default():
    """Test that the _set_init_false_fields function sets the default value for a field."""

    @dataclass
    class TestClass(Serializable):
        name: str
        computed: str = field(init=False, default="default_value")

    instance = TestClass.__new__(TestClass)
    instance.name = "test"
    assert "computed" not in instance.__dict__

    fields_tuple = fields(TestClass)
    _set_init_false_fields(instance, fields_tuple)

    assert instance.computed == "default_value"


def test_set_init_false_fields_with_default_factory():
    """Test that the _set_init_false_fields function sets the default factory for a field."""

    @dataclass
    class TestClass(Serializable):
        name: str
        dynamic: list[str] = field(init=False, default_factory=list)

    instance = TestClass(name="test")
    if hasattr(instance, "dynamic"):
        delattr(instance, "dynamic")

    fields_tuple = fields(TestClass)
    _set_init_false_fields(instance, fields_tuple)

    assert instance.dynamic == []


def test_typevar_runtime_marker_is_a_type():
    """Test that the TypeVarType is a type."""
    assert isinstance(TypeVarType, type)


def test_get_class_type_hints_returns_empty_dict_when_get_type_hints_raises(monkeypatch):
    """Test that `_get_class_type_hints` returns `{}` when `get_type_hints` raises."""

    @dataclass
    class TestClass(Serializable):
        value: int

    monkeypatch.setattr(
        "ds_common_serde_py_lib._serializable_deserialize.get_type_hints",
        lambda *_a, **_k: (_ for _ in ()).throw(Exception("boom")),
    )
    assert _get_class_type_hints(TestClass) == {}


def test_resolve_type_hint_falls_back_to_field_type_when_no_other_source_matches():
    """Test that `_resolve_type_hint_for_field` falls back to `field.type` when no hint source matches."""

    @dataclass
    class TestClass(Serializable):
        value: Any

    field_obj = fields(TestClass)[0]
    original_type = field_obj.type
    try:
        field_obj.type = None
        hint = _resolve_type_hint_for_field(
            field=field_obj,
            field_name="value",
            cls_own_hints={},
            type_var_map={},
            cls=TestClass,
        )
        assert hint is None
    finally:
        field_obj.type = original_type


def test_resolve_type_hint_logs_and_keeps_string_when_get_type_hints_raises(monkeypatch):
    """Test that string hint resolution handles get_type_hints failures and returns the string hint."""

    @dataclass
    class TestClass(Serializable):
        value: "int"

    field_obj = fields(TestClass)[0]
    original_type = field_obj.type
    try:
        field_obj.type = "int"
        monkeypatch.setattr(
            "ds_common_serde_py_lib._serializable_deserialize.get_type_hints",
            lambda *_a, **_k: (_ for _ in ()).throw(Exception("boom")),
        )
        hint = _resolve_type_hint_for_field(
            field=field_obj,
            field_name="value",
            cls_own_hints={},
            type_var_map={},
            cls=TestClass,
        )
        assert hint == "int"
    finally:
        field_obj.type = original_type


def test_set_init_false_fields_sets_default_when_class_attribute_is_removed():
    """Test that `_set_init_false_fields` sets a default when the class attribute is absent."""

    @dataclass
    class TestClass(Serializable):
        name: str
        computed: str = field(init=False, default="default_value")

    # Dataclasses typically expose `computed` as a class attribute. Remove it so
    # `hasattr(instance, "computed")` becomes False and the setter branch runs.
    if hasattr(TestClass, "computed"):
        delattr(TestClass, "computed")

    instance = TestClass.__new__(TestClass)
    instance.name = "test"
    assert not hasattr(instance, "computed")

    _set_init_false_fields(instance, fields(TestClass))
    assert instance.computed == "default_value"


def test_set_init_false_fields_sets_default_factory_when_class_attribute_is_removed():
    """Test that `_set_init_false_fields` sets a default_factory when the class attribute is absent."""

    @dataclass
    class TestClass(Serializable):
        name: str
        dynamic: list[str] = field(init=False, default_factory=list)

    if hasattr(TestClass, "dynamic"):
        delattr(TestClass, "dynamic")

    instance = TestClass.__new__(TestClass)
    instance.name = "test"
    assert not hasattr(instance, "dynamic")

    _set_init_false_fields(instance, fields(TestClass))
    assert instance.dynamic == []


def test_set_init_false_fields_does_nothing_when_no_default_is_provided():
    """Test that `_set_init_false_fields` leaves the field unset when no default/default_factory exists."""

    @dataclass
    class TestClass(Serializable):
        name: str
        unset: Any = field(init=False)

    if hasattr(TestClass, "unset"):
        delattr(TestClass, "unset")

    instance = TestClass.__new__(TestClass)
    instance.name = "test"
    assert not hasattr(instance, "unset")

    _set_init_false_fields(instance, fields(TestClass))
    assert not hasattr(instance, "unset")
