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

import logging
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from ds_common_logger_py_lib import LoggingMixin

from ._serializable_deserialize import (
    _build_type_var_map,
    _get_class_type_hints,
    _get_dataclass_fields,
    _process_field,
    _set_init_false_fields,
)
from ._serializable_serialize import _serialize_value

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping

T = TypeVar("T", bound="Serializable")


class Serializable(LoggingMixin):
    """Mixin providing ``serialize``/``deserialize`` for dataclasses."""

    __deserializers__: ClassVar[dict[str, Any]] = {}
    log_level = logging.DEBUG

    def serialize(self) -> dict[str, Any]:
        """
        Return a JSON-serializable representation of the dataclass.

        Returns:
            A dictionary representing the serialized data.
        """
        result = _serialize_value(self)
        if not isinstance(result, dict):
            raise TypeError(f"Expected dict, got {type(result)}")
        return result

    @classmethod
    def deserialize(cls: type[T], data: Mapping[str, Any]) -> T:
        """
        Create an instance from a mapping.

        Args:
            data: A dictionary representing the serialized data.

        Returns:
            An instance of the dataclass.
        """
        deserializers = getattr(cls, "__deserializers__", {}) or {}
        type_var_map = _build_type_var_map(cls)
        cls_own_hints = _get_class_type_hints(cls)
        class_fields = _get_dataclass_fields(cls)

        kwargs: dict[str, Any] = {}
        for field in class_fields:
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
