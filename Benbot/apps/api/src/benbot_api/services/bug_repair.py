"""Bug 自动修复服务 - 解析 bug.md 并创建修复任务"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.bug_report import BugReport
from ..repositories import get_bug_report, list_approved_bug_reports, save_bug_report

# Benbot/apps/api/src/benbot_api/services/bug_repair.py -> parents[5] = Benbot/
_BUG_MD_PATH = Path(__file__).resolve().parents[5] / "bug.md"
_REPAIR_LOG_PATH = Path(__file__).resolve().parents[5] / "repair_log.md"


@dataclass
class BugEntry:
    """Parsed bug entry from bug.md"""
    date: str
    username: str
    body: str
    line_number: int


def parse_bug_md() -> list[BugEntry]:
    """Parse bug.md and return all entries."""
    if not _BUG_MD_PATH.exists():
        return []
    
    content = _BUG_MD_PATH.read_text(encoding="utf-8")
    entries = []
    
    # Pattern: ## [YYYY-MM-DD] 提交者：username
    pattern = r'^## \[(\d{4}-\d{2}-\d{2})\] 提交者：(\S+)\n\n(.+?)\n\n---'
    
    lines = content.split('\n')
    current_entry = None
    current_body_lines = []
    current_line_num = 0
    
    for i, line in enumerate(lines, 1):
        match = re.match(r'^## \[(\d{4}-\d{2}-\d{2})\] 提交者：(\S+)', line)
        if match:
            # Save previous entry if exists
            if current_entry and current_body_lines:
                entries.append(BugEntry(
                    date=current_entry[0],
                    username=current_entry[1],
                    body='\n'.join(current_body_lines).strip(),
                    line_number=current_entry[2]
                ))
            current_entry = (match.group(1), match.group(2), i)
            current_body_lines = []
        elif current_entry and line.strip() and not line.startswith('---'):
            current_body_lines.append(line)
    
    # Don't forget the last entry
    if current_entry and current_body_lines:
        entries.append(BugEntry(
            date=current_entry[0],
            username=current_entry[1],
            body='\n'.join(current_body_lines).strip(),
            line_number=current_entry[2]
        ))
    
    return entries


def get_unrepaired_bugs(db: Session) -> list[dict]:
    """Get approved bugs that haven't been repaired yet."""
    approved_bugs = list_approved_bug_reports(db)
    
    unrepaired = []
    for bug in approved_bugs:
        if not bug.repaired:
            unrepaired.append({
                "id": bug.id,
                "body": bug.body,
                "approved_at": bug.approved_at.strftime("%Y-%m-%d %H:%M") if bug.approved_at else "",
            })
    
    return unrepaired


def require_approved_bug_for_repair(db: Session, bug_id: int) -> BugReport:
    bug = get_bug_report(db, bug_id)
    if not bug:
        raise ValueError("Bug not found")
    if bug.status != "approved":
        raise ValueError("Bug must be approved first")
    return bug


def mark_bug_repaired(db: Session, bug: BugReport) -> BugReport:
    bug.repaired = 1
    bug.verified = 0
    return save_bug_report(db, bug)


def log_repair_start(bug_body: str, backup_files: list[str]) -> str:
    """Log the start of a repair process."""
    _ensure_repair_log()
    now = datetime.now(UTC)
    operation_id = f"repair-{now.strftime('%Y%m%d%H%M%S%f')}"
    entry = f"""
## [{now.strftime('%Y-%m-%d %H:%M')}] 开始修复
operation_id: {operation_id}

**Bug 描述**:
{bug_body}

**备份文件**:
{chr(10).join(f'- {f}' for f in backup_files)}

status: in_progress

---
"""
    with _REPAIR_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(entry)
    return operation_id


def log_repair_complete(bug_body: str, changes_made: list[str], backup_location: str) -> str:
    """Log the completion of a repair process."""
    if not _REPAIR_LOG_PATH.exists():
        return ""

    content = _REPAIR_LOG_PATH.read_text(encoding="utf-8")
    entries = content.split("\n## [")
    if not entries:
        return ""

    rebuilt: list[str] = []
    completed_operation_id = ""
    for idx, part in enumerate(entries):
        block = part if idx == 0 else "## [" + part
        if "**Bug 描述**:\n" not in block:
            rebuilt.append(block)
            continue
        if bug_body not in block:
            rebuilt.append(block)
            continue
        if "status: in_progress" not in block:
            rebuilt.append(block)
            continue

        lines = block.splitlines()
        op_id = ""
        for line in lines:
            if line.startswith("operation_id:"):
                op_id = line.split(":", 1)[1].strip()
                break

        change_lines = "\n".join(f"- {c}" for c in changes_made)
        block = block.replace(
            "status: in_progress\n\n---",
            (
                "status: completed\n\n"
                f"**修复内容**:\n{change_lines}\n\n"
                f"**备份位置**: {backup_location}\n\n"
                "---"
            ),
            1,
        )
        rebuilt.append(block)
        completed_operation_id = op_id

    _REPAIR_LOG_PATH.write_text("".join(rebuilt), encoding="utf-8")
    return completed_operation_id


def _ensure_repair_log() -> None:
    """Ensure repair_log.md exists with header."""
    if not _REPAIR_LOG_PATH.exists():
        header = "# Bug 修复日志\n\n记录所有自动修复的操作历史。\n\n"
        _REPAIR_LOG_PATH.write_text(header, encoding="utf-8")
