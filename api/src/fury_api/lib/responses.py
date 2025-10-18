from typing import Any

from fastapi.responses import JSONResponse

from fury_api.lib.serializers import json_serializer

try:
    import msgspec
except ImportError:
    msgspec = None


class MsgSpecJSONResponse(JSONResponse):
    """JSON response using the high-performance msgspec library to serialize data to JSON."""

    def render(self, content: Any) -> bytes:
        if msgspec is None:
            raise RuntimeError("msgspec must be installed to use MsgSpecJSONResponse")
        return json_serializer(content)
