from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class JournalAudioSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence_no: int
    original_filename: str
    file_extension: str
    mime_type: str
    byte_size: int
    created_by: str
    created_at: datetime


class JournalDayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_date: date
    stt_text: str
    entry_text: str
    segment_count: int
    total_audio_bytes: int
    storage_provider: str
    storage_status: str
    transcript_status: str
    combined_audio_object_key: str | None = None
    combined_audio_url: str | None = None
    last_error_message: str
    last_recorded_at: datetime | None = None
    last_transcribed_at: datetime | None = None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    playback_url: str | None = None
    segments: list[JournalAudioSegmentRead] = Field(default_factory=list)


class JournalDayListItem(BaseModel):
    entry_date: str
    segment_count: int
    transcript_status: str
    storage_status: str
    updated_at: datetime
    transcript_preview: str


class JournalTextUpdate(BaseModel):
    entry_text: str = Field(default="", max_length=200000)


class JournalIngestResponse(BaseModel):
    day: JournalDayRead
    warnings: list[str] = Field(default_factory=list)
