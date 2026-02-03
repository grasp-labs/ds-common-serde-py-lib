"""
**File:** ``06_omit_fields.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Omit dataclass fields from serialization using field metadata.
"""

from dataclasses import dataclass, field
import logging

from ds_common_serde_py_lib import Serializable
from ds_common_logger_py_lib import Logger

Logger.configure(level=logging.DEBUG)
logger = Logger.get_logger(__name__)


@dataclass
class Example(Serializable):
    a: int
    secret: str = field(metadata={"serialize": False})


def main() -> None:
    obj = Example(a=1, secret="nope")
    payload = obj.serialize()
    logger.debug("payload: %s", payload)


if __name__ == "__main__":
    main()
