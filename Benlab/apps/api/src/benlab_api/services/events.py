from __future__ import annotations

from datetime import datetime
from io import BytesIO

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from benlab_api.core.config import get_settings

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = ImageDraw = ImageFont = None


def parse_datetime_local(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def format_datetime_local(value: datetime | None) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%dT%H:%M")


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt=settings.EVENT_SHARE_TOKEN_SALT)


def generate_event_share_token(event_id: int) -> str:
    return _serializer().dumps({"event_id": event_id})


def verify_event_share_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = _serializer().loads(token, max_age=settings.EVENT_SHARE_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    event_id = payload.get("event_id")
    if isinstance(event_id, int):
        return event_id
    try:
        return int(event_id)
    except (TypeError, ValueError):
        return None


def generate_poster_png(title: str, detail_url: str) -> bytes:
    # Fallback when Pillow is unavailable.
    if Image is None:
        return b""
    img = Image.new("RGB", (1080, 1920), color=(248, 249, 252))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.text((80, 120), "Benlab Event", fill=(28, 45, 90), font=font)
    draw.text((80, 200), title or "Untitled Event", fill=(0, 0, 0), font=font)
    draw.text((80, 320), detail_url or "", fill=(64, 64, 64), font=font)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
