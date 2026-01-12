"""
**File:** ``__init__.py``
**Region:** ``ds-common-serde-py-lib``

Description
-----------
A Python package from the ds-common-serde-py-lib library.

Example
-------
.. code-block:: python

    from ds_common_serde_py_lib import __version__

    print(f"Package version: {__version__}")
"""

from importlib.metadata import version

from .errors import DeserializationError, SerializationError
from .serializable import Serializable

__version__ = version("ds-common-serde-py-lib")
__all__ = ["DeserializationError", "Serializable", "SerializationError", "__version__"]
