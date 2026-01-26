"""
**File:** ``_serializable_deserialize.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Defines internal helpers used by ``Serializable.deserialize()`` for inspecting
dataclass fields and type hints, resolving type variables, converting field
values, and setting ``init=False`` fields after construction.

Example
-------
.. code-block:: python

    from dataclasses import dataclass, field

    from ds_common_serde_py_lib import Serializable


    @dataclass
    class WithInitFalse(Serializable):
        name: str
        computed: str = field(init=False, default="computed")


    obj = WithInitFalse.deserialize({"name": "x"})
    assert obj.computed == "computed"
"""

from __future__ import annotations

from dataclasses import MISSING
from dataclasses import fields as dc_fields
from typing import Any, TypeVar, cast, get_type_hints

from ds_common_logger_py_lib import Logger

from ._serializable_convert import _convert_value

logger = Logger.get_logger(__name__, package=True)

TypeVarType = type(TypeVar("_T_RUNTIME_MARKER_"))

T = TypeVar("T")


def _build_type_var_map(cls: type) -> dict[Any, Any]:
    """
    Build a mapping from TypeVars to their concrete types.

    Args:
        cls: The class to build the type var map for.

    Returns:
        A mapping from TypeVars to their concrete types.
    """
    from typing import get_args, get_origin  # noqa: PLC0415

    type_var_map: dict[Any, Any] = {}
    for base_alias in getattr(cls, "__orig_bases__", []) or []:
        origin = get_origin(base_alias)
        if origin is None:
            continue
        args = get_args(base_alias)
        try:
            params = origin.__parameters__
        except (AttributeError, Exception):
            continue
        if params and args:
            for param, arg in zip(params, args, strict=True):
                type_var_map[param] = arg
    return type_var_map


def _get_class_type_hints(cls: type) -> dict[str, Any]:
    """
    Get type hints from the class itself (best-effort).

    Args:
        cls: The class to get the type hints for.

    Returns:
        A dictionary of type hints.
    """
    try:
        return get_type_hints(cls) or {}
    except Exception as exc:
        logger.debug("Failed to get type hints for %s: %s", cls.__name__, exc)
        return {}


def _get_dataclass_fields(cls: type) -> tuple[Any, ...]:
    """
    Get dataclass fields for the given class.

    Args:
        cls: The class to get the dataclass fields for.

    Returns:
        A tuple of dataclass fields.
    """
    try:
        return dc_fields(cast("Any", cls))
    except Exception as exc:
        raise Exception(
            str(exc),
            {
                "type": type(exc).__name__,
                "class_name": cls.__name__,
            },
        ) from exc


def _resolve_type_hint_for_field(
    field: Any,
    field_name: str,
    cls_own_hints: dict[str, Any],
    type_var_map: dict[Any, Any],
    cls: type,
) -> Any:
    """
    Resolve the type hint for a dataclass field.

    Args:
        field: The field to resolve the type hint for.
        field_name: The name of the field.
        cls_own_hints: The type hints for the class.
        type_var_map: A mapping from TypeVars to their concrete types.
        cls: The class to resolve the type hint for.

    Returns:
        The resolved type hint.
    """
    if field.type and not isinstance(field.type, TypeVarType) and field.type is not Any:
        hint = field.type
    elif field_name in cls_own_hints:
        hint = cls_own_hints[field_name]
    else:
        hint = field.type

    if isinstance(hint, TypeVarType):
        hint = type_var_map.get(hint, getattr(hint, "__bound__", Any))

    if isinstance(hint, str):
        try:
            resolved_hints = get_type_hints(cls)
            if field_name in resolved_hints:
                hint = resolved_hints[field_name]
        except Exception as exc:
            logger.debug(
                "Failed to resolve type hint '%s' for %s.%s: %s",
                hint,
                cls.__name__,
                field_name,
                exc,
            )

    return hint


def _process_field(
    field: Any,
    raw_value: Any,
    deserializers: dict[str, Any],
    cls_own_hints: dict[str, Any],
    type_var_map: dict[Any, Any],
    cls: type,
) -> Any:
    """
    Process a single field during deserialization.

    Args:
        field: The field to process.
        raw_value: The raw value of the field.
        deserializers: A dictionary of deserializers.
        cls_own_hints: The type hints for the class.
        type_var_map: A mapping from TypeVars to their concrete types.
        cls: The class to process the field for.

    Returns:
        The processed value.
    """
    converter = deserializers.get(field.name)
    if callable(converter):
        return converter(raw_value)

    hint = _resolve_type_hint_for_field(
        field=field,
        field_name=field.name,
        cls_own_hints=cls_own_hints,
        type_var_map=type_var_map,
        cls=cls,
    )
    return _convert_value(raw_value, hint)


def _set_init_false_fields(instance: Any, class_fields: tuple[Any, ...]) -> None:
    """
    Set fields with init=False and defaults after instance creation.

    Args:
        instance: The instance to set the fields for.
        class_fields: A tuple of dataclass fields.
    """
    for field in class_fields:
        if not field.init and not hasattr(instance, field.name):
            if field.default is not MISSING:
                setattr(instance, field.name, field.default)
            elif field.default_factory is not MISSING:
                setattr(instance, field.name, field.default_factory())
