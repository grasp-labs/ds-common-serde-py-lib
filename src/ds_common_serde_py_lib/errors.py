"""
**File:** ``errors.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Defines exception classes for (de)serialization operations.

Example
-------
.. code-block:: python

    from ds_common_serde_py_lib.errors import DeserializationError, SerializationError

    ser_exc = SerializationError()
    assert ser_exc.status_code == 500
    assert ser_exc.message == "Serialization failed"
    assert ser_exc.code == "DS_SERIALIZATION_ERROR"
    assert ser_exc.details == {}

    deser_exc = DeserializationError(details={"field": "name"})
    assert deser_exc.code == "DS_DESERIALIZATION_ERROR"
"""

from typing import Any


class SerdeError(Exception):
    """Base exception for ds-common-serde errors."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a serde exception.

        Args:
            message: Human-readable error message.
            code: Machine-readable error code.
            status_code: HTTP-ish status code associated with the error.
            details: Optional extra details to help diagnose the error.

        Example:
            >>> exc = SerdeError(message="Boom", code="DS_SERDE_ERROR")
            >>> exc.code
            'DS_SERDE_ERROR'
        """
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SerializationError(SerdeError):
    """Exception raised when serialization fails."""

    def __init__(
        self,
        message: str = "Serialization failed",
        code: str = "DS_SERIALIZATION_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class DeserializationError(SerdeError):
    """Exception raised when deserialization fails."""

    def __init__(
        self,
        message: str = "Deserialization failed",
        code: str = "DS_DESERIALIZATION_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a deserialization error.

        Args:
            message: Human-readable error message.
            code: Machine-readable error code.
            status_code: HTTP-ish status code associated with the error.
            details: Optional extra details to help diagnose the error.

        Example:
            >>> exc = DeserializationError()
            >>> exc.code
            'DS_DESERIALIZATION_ERROR'
        """
        super().__init__(message=message, code=code, status_code=status_code, details=details)
