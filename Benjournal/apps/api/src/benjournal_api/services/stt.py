from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from benjournal_api.core.config import get_settings


@dataclass
class TranscriptionResult:
    provider: str
    text: str


class STTError(RuntimeError):
    pass


def transcribe_audio(local_path: Path, *, entry_date: date, segment_count: int) -> TranscriptionResult:
    settings = get_settings()
    provider = settings.STT_PROVIDER.strip().lower()
    if provider == "mock":
        return _mock_transcription(local_path, entry_date=entry_date, segment_count=segment_count)
    if provider == "openai":
        return _openai_transcription(local_path)
    raise STTError(f"不支持的 STT 提供方: {settings.STT_PROVIDER}")


def _mock_transcription(local_path: Path, *, entry_date: date, segment_count: int) -> TranscriptionResult:
    size_kb = max(1, round(local_path.stat().st_size / 1024))
    text = (
        f"[mock] {entry_date.isoformat()} 已累计 {segment_count} 段语音，"
        f"合并文件 {local_path.name}，大小约 {size_kb} KB。"
    )
    return TranscriptionResult(provider="mock", text=text)


def _openai_transcription(local_path: Path) -> TranscriptionResult:
    settings = get_settings()
    if not settings.STT_OPENAI_API_KEY.strip():
        raise STTError("缺少 STT_OPENAI_API_KEY，无法调用 OpenAI STT。")
    if not settings.STT_OPENAI_MODEL.strip():
        raise STTError("缺少 STT_OPENAI_MODEL，无法调用 OpenAI STT。")

    try:
        import httpx
    except ImportError as exc:
        raise STTError("未安装 httpx，无法调用 OpenAI STT。") from exc

    with local_path.open("rb") as audio_file:
        response = httpx.post(
            f"{settings.STT_OPENAI_BASE_URL.rstrip('/')}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.STT_OPENAI_API_KEY}"},
            data={
                "model": settings.STT_OPENAI_MODEL,
                "prompt": settings.STT_OPENAI_PROMPT,
            },
            files={"file": (local_path.name, audio_file, "application/octet-stream")},
            timeout=180,
        )

    if response.status_code >= 400:
        raise STTError(f"OpenAI STT 调用失败: {response.status_code}")
    payload = response.json()
    text = str(payload.get("text", "")).strip()
    if not text:
        raise STTError("OpenAI STT 未返回可用文本。")
    return TranscriptionResult(provider="openai", text=text)
