"""
**File:** ``test_serializable.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Tests for the public ``Serializable`` facade (``serialize``/``deserialize``).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Generic, TypeVar
from uuid import UUID, uuid4

import pytest

from ds_common_serde_py_lib.errors import DeserializationError, SerializationError
from ds_common_serde_py_lib.serializable import Serializable


@dataclass(kw_only=True)
class DatasetTypedProperties(Serializable):
    """
    The object containing the typed properties of the dataset.
    """

    pass


class Color(Enum):
    RED = "red"
    BLUE = "blue"


@dataclass
class Child(Serializable):
    count: int


@dataclass
class Parent(Serializable):
    name: str
    child: Child
    tags: list[str]
    created_at: datetime
    uid: UUID
    color: Color
    values: list[int]
    mapping: dict[str, int]
    optional_note: str | None = None


def test_serialize_handles_nested_and_special_types():
    """Test that the serialize method handles nested and special types."""
    created_at = datetime(2024, 1, 1, 12, 0, 0)
    uid = uuid4()
    parent = Parent(
        name="parent",
        child=Child(count=3),
        tags=["a", "b"],
        created_at=created_at,
        uid=uid,
        color=Color.RED,
        values=[1, 2],
        mapping={"one": 1},
        optional_note=None,
    )

    serialized = parent.serialize()

    assert serialized["name"] == "parent"
    assert serialized["child"] == {"count": 3}
    assert serialized["tags"] == ["a", "b"]
    assert serialized["created_at"] == created_at.isoformat()
    assert serialized["uid"] == str(uid)
    assert serialized["color"] == Color.RED.value
    assert serialized["mapping"] == {"one": 1}


def test_deserialize_converts_types():
    """Test that the deserialize method converts types."""
    uid = uuid4()
    created_at = datetime(2024, 2, 1, 8, 0, 0)
    data = {
        "name": "parent",
        "child": {"count": "5"},
        "tags": ["x", "y"],
        "created_at": created_at.isoformat(),
        "uid": str(uid),
        "color": "blue",
        "values": ["1", "2"],
        "mapping": {"first": "10"},
        "optional_note": None,
    }

    parent = Parent.deserialize(data)

    assert parent.child.count == 5
    assert parent.uid == uid
    assert parent.created_at == created_at
    assert parent.color is Color.BLUE
    assert parent.values == [1, 2]
    assert parent.mapping == {"first": 10}
    assert parent.optional_note is None


def test_deserializers_override_field():
    """Test that the deserializers override the field."""

    @dataclass
    class CustomModel(Serializable):
        __deserializers__: ClassVar[dict[str, Any]] = {"name": lambda value: value.title()}

        name: str
        amount: int

    result = CustomModel.deserialize({"name": "john doe", "amount": "7"})

    assert result.name == "John Doe"
    assert result.amount == 7


def test_typevar_resolution_and_conversion():
    """Test that the typevar resolution and conversion works."""
    T = TypeVar("T")

    @dataclass
    class GenericModel(Serializable, Generic[T]):
        item: T

    @dataclass
    class IntModel(GenericModel[int]):
        pass

    model = IntModel.deserialize({"item": "9"})

    assert model.item == 9
    assert isinstance(model.item, int)


def test_serialize_non_dataclass_raises():
    """Test that the serialize method raises an error if the class is not a dataclass."""

    class PlainSerializable(Serializable):
        pass

    with pytest.raises(SerializationError) as exc:
        PlainSerializable().serialize()
    assert exc.value.details.get("class_name") == "PlainSerializable"


def test_deserialize_non_dataclass_raises():
    """Test that the deserialize method raises an error if the class is not a dataclass."""

    class NonDataclassSerializable(Serializable):
        __module__ = "tests.libs.models.test_serializable"

    with pytest.raises(DeserializationError) as exc:
        NonDataclassSerializable.deserialize({"value": 1})
    assert exc.value.details.get("class_name") == "NonDataclassSerializable"


def test_deserialize_sets_init_false_fields():
    """Test that the deserialize method sets the init false fields."""

    @dataclass
    class WithInitFalse(Serializable):
        name: str
        computed: str = field(init=False, default="computed")
        dynamic: str = field(init=False, default_factory=lambda: "dynamic")

    instance = WithInitFalse.deserialize({"name": "example"})

    assert instance.computed == "computed"
    assert instance.dynamic == "dynamic"


def test_forward_reference_resolution():
    """Test that the forward reference resolution works."""

    @dataclass
    class ForwardParent(Serializable):
        child: "Child"

    parent = ForwardParent.deserialize({"child": {"count": "9"}})
    assert parent.child == Child(count=9)


def test_dataset_typed_properties_specialization_is_not_guessed():
    """Test that the dataset typed properties specialization is not guessed."""

    @dataclass
    class MinimalDatasetProps(DatasetTypedProperties):
        foo: int

    @dataclass
    class ExtendedDatasetProps(DatasetTypedProperties):
        foo: int
        bar: str

    @dataclass
    class DatasetPropsContainer(Serializable):
        props: DatasetTypedProperties

    raw = {"props": {"foo": 1, "bar": "value"}}
    result = DatasetPropsContainer.deserialize(raw)

    assert isinstance(result.props, DatasetTypedProperties)
    assert result.props.serialize() == {}
