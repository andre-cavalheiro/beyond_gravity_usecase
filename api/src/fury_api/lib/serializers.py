from typing import Any

import msgspec
from sqlmodel import SQLModel

__all__ = ["json_serializer", "json_deserializer", "msgpack_serializer", "msgpack_deserializer"]


def _default_enc_hook(val: Any) -> Any:
    if isinstance(val, SQLModel):
        return val.dict(by_alias=True)
    return val


def _default_dec_hook(val: Any) -> Any:
    return val


def json_serializer(obj: Any) -> bytes:
    return msgspec.json.encode(obj, enc_hook=_default_enc_hook)


def json_deserializer(obj: str | bytes) -> Any:
    return msgspec.json.decode(obj, dec_hook=_default_dec_hook)
