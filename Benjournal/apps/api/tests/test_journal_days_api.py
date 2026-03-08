from __future__ import annotations

import io
import wave


def _login(client):
    response = client.post(
        "/login",
        data={"username": "benbenbuben", "password": "benbenbuben", "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _wav_bytes(*, sample_rate: int = 16000, frames: int = 1600) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(b"\x00\x00" * frames)
    return buffer.getvalue()


def test_journal_audio_ingest_and_text_update(client):
    _login(client)

    first = client.post(
        "/api/journal-days/2026-03-08/segments",
        files={"audio_file": ("morning.wav", _wav_bytes(frames=1200), "audio/wav")},
    )
    assert first.status_code == 201
    payload = first.json()
    assert payload["day"]["segment_count"] == 1
    assert payload["day"]["storage_status"] == "ready"
    assert payload["day"]["transcript_status"] == "ready"
    assert payload["day"]["entry_text"].startswith("[mock] 2026-03-08")

    second = client.post(
        "/api/journal-days/2026-03-08/segments",
        files={"audio_file": ("night.wav", _wav_bytes(frames=2400), "audio/wav")},
    )
    assert second.status_code == 201
    assert second.json()["day"]["segment_count"] == 2

    detail = client.get("/api/journal-days/2026-03-08")
    assert detail.status_code == 200
    assert len(detail.json()["segments"]) == 2

    updated = client.patch(
        "/api/journal-days/2026-03-08",
        json={"entry_text": "手工修正后的完整日记文本。"},
    )
    assert updated.status_code == 200
    assert updated.json()["entry_text"] == "手工修正后的完整日记文本。"

    listed = client.get("/api/journal-days")
    assert listed.status_code == 200
    assert listed.json()[0]["entry_date"] == "2026-03-08"
