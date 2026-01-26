"""
**File:** ``serializable.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Defines the public ``Serializable`` mixin for dataclasses, providing
``serialize()`` and ``deserialize()``.

Example
-------
.. code-block:: python

    from dataclasses import dataclass

    from ds_common_serde_py_lib import Serializable


    @dataclass
    class Child(Serializable):
        count: int


    payload = Child(count=1).serialize()
    obj = Child.deserialize(payload)
    assert obj == Child(count=1)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from ds_common_logger_py_lib import Logger

from ._serializable_deserialize import (
    _build_type_var_map,
    _get_class_type_hints,
    _get_dataclass_fields,
    _process_field,
    _set_init_false_fields,
)
from ._serializable_serialize import _serialize_value
from .errors import DeserializationError, SerializationError

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping

T = TypeVar("T", bound="Serializable")

logger = Logger.get_logger(__name__, package=True)


class Serializable:
    """Mixin providing ``serialize``/``deserialize`` for dataclasses."""

    __deserializers__: ClassVar[dict[str, Any]] = {}

    def serialize(self) -> dict[str, Any]:
        """
        Return a JSON-serializable representation of the dataclass.

        Returns:
            A dictionary representing the serialized data.

        Raises:
            SerializationError: If serialization fails or does not produce a mapping.
        """
        try:
            result = _serialize_value(self)
        except Exception as exc:
            raise SerializationError(
                message=str(exc),
                details={
                    "class_name": type(self).__name__,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        if not isinstance(result, dict):
            raise SerializationError(
                message="Serialization did not produce an object",
                details={
                    "class_name": type(self).__name__,
                    "actual_type": type(result).__name__,
                },
            )
        return result

    @classmethod
    def deserialize(cls: type[T], data: Mapping[str, Any]) -> T:
        """
        Create an instance from a mapping.

        Args:
            data: A dictionary representing the serialized data.

        Returns:
            An instance of the dataclass.

        Raises:
            DeserializationError: If `data` cannot be converted into an instance.
        """
        if not isinstance(data, dict) and not hasattr(data, "get"):
            raise DeserializationError(
                message="Expected a mapping for deserialization",
                details={
                    "class_name": cls.__name__,
                    "actual_type": type(data).__name__,
                },
            )

        deserializers = getattr(cls, "__deserializers__", {}) or {}
        try:
            type_var_map = _build_type_var_map(cls)
            cls_own_hints = _get_class_type_hints(cls)
            class_fields = _get_dataclass_fields(cls)
        except Exception as exc:
            raise DeserializationError(
                message=str(exc),
                details={
                    "class_name": cls.__name__,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        kwargs: dict[str, Any] = {}
        current_field_name: str | None = None
        try:
            for field in class_fields:
                current_field_name = field.name
                if field.name not in data:
                    continue

                raw_value = data[field.name]
                converted_value = _process_field(
                    field=field,
                    raw_value=raw_value,
                    deserializers=deserializers,
                    cls_own_hints=cls_own_hints,
                    type_var_map=type_var_map,
                    cls=cls,
                )
                kwargs[field.name] = converted_value

            instance = cls(**kwargs)
            _set_init_false_fields(instance, class_fields)
            return instance
        except Exception as exc:
            raise DeserializationError(
                message=str(exc),
                details={
                    "class_name": cls.__name__,
                    "field": current_field_name,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "provided_keys": sorted(getattr(data, "keys", lambda: [])()),
                    "constructed_keys": sorted(kwargs.keys()),
                },
            ) from exc
