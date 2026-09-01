from io import BytesIO

import qrcode
from fastapi.responses import StreamingResponse


def generate_qr_code(url: str) -> StreamingResponse:
    """Generate a QR code image for the given URL, return as StreamingResponse (PNG)."""
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
