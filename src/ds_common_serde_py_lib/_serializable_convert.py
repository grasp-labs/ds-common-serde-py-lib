"""
**File:** ``_serializable_convert.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Defines value conversion helpers used by ``Serializable.deserialize()``,
including recursive conversion for typed iterables/mappings/unions and support
for ``deserialize()``-capable classes.

Example
-------
.. code-block:: python

    from dataclasses import dataclass

    from ds_common_serde_py_lib import Serializable


    @dataclass
    class Child(Serializable):
        count: int


    obj = Child.deserialize({"count": "7"})
    assert obj.count == 7
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import Enum
from typing import Any, cast, get_args, get_origin, get_type_hints


def _is_direct_dataclass_serializable(cls: type) -> bool:
    """True only for classes directly decorated with @dataclass that also inherit Serializable.

    Implemented with a runtime import to avoid circular imports after splitting
    the implementation across multiple modules.

    Args:
        cls: The class to check.

    Returns:
        True if the class is a direct dataclass Serializable, False otherwise.
    """
    try:
        from ds_common_serde_py_lib.serializable import Serializable  # noqa: PLC0415
    except Exception:
        return False

    return "__dataclass_fields__" in getattr(cls, "__dict__", {}) and Serializable in getattr(cls, "__mro__", ())


def _convert_value(value: Any, type_hint: Any) -> Any:
    """Convert ``value`` into the type described by ``type_hint``.

    This is the main conversion routine used during deserialization.
    It performs best-effort conversion guided by `type_hint`:
    - For concrete runtime types (including `Enum`), attempts constructor-based conversion.
    - For mappings and types that explicitly support `deserialize`, calls `deserialize` when unambiguous.
    - For typed containers (list/tuple/set/dict), converts contents recursively.
    - For unions (including Optionals), tries each member until one succeeds.

    Forward references are intentionally left unresolved to avoid import-time cycles.

    Args:
        value: The value to convert.
        type_hint: The type to convert the value to.

    Returns:
        The converted value (may be unchanged if no applicable conversion strategy is found).
    """
    if value is None or type_hint is Any:
        return value

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    origin_deserialized = _maybe_deserialize_from_origin(value=value, origin=origin)
    if origin_deserialized is not _NOT_SET:
        return origin_deserialized

    if origin is None and isinstance(type_hint, type):
        return _convert_to_concrete_type(value=value, type_hint=type_hint)

    iterable_converted = _convert_typed_iterable(value=value, origin=origin, args=args)
    if iterable_converted is not _NOT_SET:
        return iterable_converted

    mapping_converted = _convert_typed_mapping(value=value, origin=origin, args=args)
    if mapping_converted is not _NOT_SET:
        return mapping_converted

    union_converted = _convert_union(value=value, origin=origin, args=args)
    if union_converted is not _NOT_SET:
        return union_converted

    return value


_NOT_SET: object = object()


def _maybe_deserialize_from_origin(*, value: Any, origin: Any) -> Any:
    """Attempt origin-based deserialization for parametrized type hints.

    This is used for hints where `get_origin(type_hint)` returns a type that may
    provide a `deserialize` method (or be a direct dataclass `Serializable`).

    Args:
        value: The raw value to convert.
        origin: The origin type as returned by `typing.get_origin`.

    Returns:
        - The deserialized object when applicable.
        - `_NOT_SET` if this helper does not apply.
    """
    if origin is None or not isinstance(origin, type) or not isinstance(value, Mapping):
        return _NOT_SET

    if _is_direct_dataclass_serializable(origin) or (
        "deserialize" in getattr(origin, "__dict__", {}) and callable(getattr(origin, "deserialize", None))
    ):
        return cast("Any", origin).deserialize(value)

    return _NOT_SET


def _convert_to_concrete_type(*, value: Any, type_hint: type) -> Any:
    """Convert `value` to a concrete runtime `type_hint`.

    Conversion strategy:
    - Return `value` if it already matches `type_hint`.
    - If `type_hint` is an `Enum`, construct it from `value`.
    - If `value` is a mapping and `type_hint` supports `deserialize`, call it.
    - If `value` is a mapping, try kwarg-based construction from `__init__`.
    - Special-case `datetime` from ISO strings.
    - Fall back to `type_hint(value)` construction.

    Args:
        value: The raw value to convert.
        type_hint: The concrete runtime type to convert to.

    Returns:
        The converted value.

    Raises:
        ValueError: When converting to `datetime` and the value is not convertible.
        Exception: Any exception raised by enum construction, `deserialize`, or constructors.
    """
    if isinstance(value, type_hint):
        return value

    if issubclass(type_hint, Enum):
        return type_hint(value)

    mapping_deserialized = _maybe_deserialize_from_type(value=value, type_hint=type_hint)
    if mapping_deserialized is not _NOT_SET:
        return mapping_deserialized

    if isinstance(value, Mapping):
        constructed = _try_construct_from_mapping(value=value, type_hint=type_hint)
        if constructed is not _NOT_SET:
            return constructed

    if type_hint is datetime:
        return _convert_datetime(value=value)

    return type_hint(value)  # type: ignore[call-arg]


def _maybe_deserialize_from_type(*, value: Any, type_hint: type) -> Any:
    """Attempt deserialization using `type_hint.deserialize` when unambiguous.

    Args:
        value: The raw value (must be a mapping).
        type_hint: The target class.

    Returns:
        - The deserialized object when applicable.
        - `_NOT_SET` if this helper does not apply.
    """
    if not isinstance(value, Mapping):
        return _NOT_SET

    if _is_direct_dataclass_serializable(type_hint) or (
        "deserialize" in getattr(type_hint, "__dict__", {}) and callable(getattr(type_hint, "deserialize", None))
    ):
        return cast("Any", type_hint).deserialize(value)

    return _NOT_SET


def _try_construct_from_mapping(*, value: Mapping[str, Any], type_hint: type) -> Any:
    """Try instantiating `type_hint(**kwargs)` from a mapping.

    Uses `inspect.signature(type_hint.__init__)` to select keyword args and
    `typing.get_type_hints(type_hint.__init__)` to recursively convert values.
    If the signature cannot be inspected, falls back to passing the mapping as kwargs.

    Args:
        value: Mapping of constructor arguments.
        type_hint: Target class to instantiate.

    Returns:
        - An instance of `type_hint` on success.
        - `_NOT_SET` if construction fails with `TypeError`.
    """
    try:
        init_hints = get_type_hints(type_hint.__init__)  # type: ignore[misc]
    except Exception:
        init_hints = {}

    try:
        sig = inspect.signature(type_hint.__init__)  # type: ignore[misc]
    except (TypeError, ValueError):
        sig = None

    kwargs: dict[str, Any] = {}
    if sig is not None:
        for name in sig.parameters:
            if name == "self":
                continue
            if name in value:
                expected = init_hints.get(name, Any)
                kwargs[name] = _convert_value(value[name], expected)
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            for k, v in dict(value).items():
                if k not in kwargs:
                    kwargs[k] = v
    else:
        kwargs = dict(value)

    try:
        return type_hint(**kwargs)
    except TypeError:
        return _NOT_SET


def _convert_datetime(*, value: Any) -> datetime:
    """Convert a value to `datetime`.

    Args:
        value: The input value.

    Returns:
        A `datetime` parsed from an ISO-8601 string.

    Raises:
        ValueError: If `value` is not a string convertible via `datetime.fromisoformat`.
    """
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError(f"Cannot convert {type(value)} to datetime")


def _convert_typed_iterable(*, value: Any, origin: Any, args: tuple[Any, ...]) -> Any:
    """Convert a typed iterable (`list[T]`, `tuple[T]`, `set[T]`, `Iterable[T]`).

    Args:
        value: The raw iterable value.
        origin: The typing origin.
        args: The typing args.

    Returns:
        - The converted container when applicable.
        - `_NOT_SET` if this helper does not apply.
    """
    if origin not in (list, tuple, set, Iterable):
        return _NOT_SET

    inner = args[0] if args else Any
    converted_list = [_convert_value(v, inner) for v in (list(value) if not isinstance(value, list) else value)]
    if origin is list or origin is Iterable:
        return converted_list
    if origin is tuple:
        return tuple(converted_list)
    if origin is set:
        return set(converted_list)
    return _NOT_SET


def _convert_typed_mapping(*, value: Any, origin: Any, args: tuple[Any, ...]) -> Any:
    """Convert a typed mapping (`dict[K, V]` / `Mapping[K, V]`).

    Args:
        value: The raw mapping value.
        origin: The typing origin.
        args: The typing args.

    Returns:
        - The converted mapping when applicable.
        - `_NOT_SET` if this helper does not apply.
    """
    if origin not in (dict, Mapping):
        return _NOT_SET

    key_t = args[0] if len(args) == 2 else Any
    val_t = args[1] if len(args) == 2 else Any
    return {_convert_value(k, key_t): _convert_value(v, val_t) for k, v in dict(value).items()}


def _convert_union(*, value: Any, origin: Any, args: tuple[Any, ...]) -> Any:
    """Convert a union (`typing.Union[...]` or PEP 604 `X | Y`).

    Attempts conversion against each member type in order, returning the first
    successful conversion.

    Args:
        value: The raw value to convert.
        origin: The typing origin for the union.
        args: The union member types.

    Returns:
        - Converted value when a member conversion succeeds.
        - `None` when union includes NoneType and `value` is None.
        - `_NOT_SET` if this helper does not apply.

    Raises:
        Exception: Re-raises the last conversion error when all non-None members fail.
    """
    typing_union = getattr(__import__("typing"), "Union", None)
    is_types_union = False
    try:
        types_union = __import__("types").UnionType
    except (ImportError, AttributeError):
        types_union = None
        is_types_union = getattr(origin, "__module__", None) == "types" and getattr(origin, "__name__", None) == "UnionType"

    if origin is not typing_union and origin is not types_union and not is_types_union:
        return _NOT_SET

    last_err: Exception | None = None
    for arg in args:
        if arg is type(None):
            if value is None:
                return None
            continue
        try:
            return _convert_value(value, arg)
        except Exception as exc:
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    return _NOT_SET
