"""
**File:** ``06_omit_fields.py``
**Region:** ``ds_common_serde_py_lib``

Description
-----------
Omit dataclass fields from serialization using field metadata.

Fields with metadata {'serialize': False} are omitted from the output.
Fields with metadata {'mask': True} are included with placeholder '********'.
Fields with metadata {'mask': '<str>'} use that string as the serialized value.

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
    dont_serialize: str = field(metadata={"serialize": False})
    secret: str = field(metadata={"mask": True})
    token: str = field(default="sensitive", metadata={"mask": "••••••••"})


def main() -> None:
    obj = Example(a=1, dont_serialize="nope", secret="my-secret", token="my-token")
    payload = obj.serialize()
    logger.debug("payload: %s", payload)


if __name__ == "__main__":
    main()
