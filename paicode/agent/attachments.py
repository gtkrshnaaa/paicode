import base64
from dataclasses import dataclass

MAX_IMAGE_BYTES = 10_000_000


@dataclass
class ImageAttachment:
    token: str
    mime: str
    data: bytes

    @property
    def data_url(self) -> str:
        payload = base64.b64encode(self.data).decode("ascii")
        return f"data:{self.mime};base64,{payload}"
