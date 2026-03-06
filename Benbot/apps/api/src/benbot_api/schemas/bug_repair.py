from __future__ import annotations

from pydantic import BaseModel


class UnrepairedBugItem(BaseModel):
    id: int
    body: str
    approved_at: str


class RepairPrepareResponse(BaseModel):
    ok: bool
    bug_id: int
    backup_path: str
    backed_up_files: list[str]
    bug_body: str
    repair_log_operation_id: str


class RepairCompleteResponse(BaseModel):
    ok: bool
    bug_id: int
    repair_log_operation_id: str
    repaired: bool


class BackupItem(BaseModel):
    filename: str
    path: str
    created_at: str
    size_bytes: int
