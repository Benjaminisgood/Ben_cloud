from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.bug_report import BugReport
from ..repositories import (
    create_bug_report,
    get_bug_report,
    get_user_by_id,
    list_approved_bug_reports_with_reporter,
    list_pending_bug_reports_with_reporter,
    save_bug_report,
)

# Benbot/apps/api/src/benbot_api/services/bugs.py -> parents[5] = Benbot/
_BUG_MD_PATH = Path(__file__).resolve().parents[5] / "bug.md"


def create_bug(db: Session, reporter_id: int, body: str) -> BugReport:
    """Create a new pending bug report."""
    return create_bug_report(db, reporter_id=reporter_id, body=body)


def list_pending(db: Session) -> list[dict]:
    """Return all pending bug reports with reporter username."""
    rows = list_pending_bug_reports_with_reporter(db)
    return [_format_bug(bug, username) for bug, username in rows]


def list_approved(db: Session) -> list[dict]:
    """Return all approved bug reports with reporter username and repair status."""
    rows = list_approved_bug_reports_with_reporter(db)
    return [{
        **_format_bug(bug, username),
        "repaired": bool(bug.repaired),
        "verified": bool(bug.verified),
    } for bug, username in rows]


def approve_bug(db: Session, bug_id: int) -> dict:
    """Approve a bug report, append it to bug.md, return formatted dict."""
    bug = get_bug_report(db, bug_id)
    if not bug:
        raise ValueError(f"bug_report {bug_id} not found")
    if bug.status != "pending":
        raise ValueError(f"bug_report {bug_id} is not pending (status={bug.status})")

    reporter = get_user_by_id(db, bug.reporter_id)
    username = reporter.username if reporter else f"user#{bug.reporter_id}"

    now = datetime.utcnow()
    bug.status = "approved"
    bug.approved_at = now
    save_bug_report(db, bug)

    _append_to_bug_md(
        date_str=now.strftime("%Y-%m-%d"),
        username=username,
        body=bug.body,
    )

    return _format_bug(bug, username)


def reject_bug(db: Session, bug_id: int) -> dict:
    """Reject a pending bug report."""
    bug = get_bug_report(db, bug_id)
    if not bug:
        raise ValueError(f"bug_report {bug_id} not found")
    if bug.status != "pending":
        raise ValueError(f"bug_report {bug_id} is not pending (status={bug.status})")

    reporter = get_user_by_id(db, bug.reporter_id)
    username = reporter.username if reporter else f"user#{bug.reporter_id}"

    bug.status = "rejected"
    save_bug_report(db, bug)
    return _format_bug(bug, username)


def verify_bug(db: Session, bug_id: int) -> dict:
    """Mark a bug as verified by admin and add to repaired section in bug.md."""
    bug = get_bug_report(db, bug_id)
    if not bug:
        raise ValueError(f"bug_report {bug_id} not found")
    if bug.status != "approved":
        raise ValueError(f"bug_report {bug_id} is not approved (status={bug.status})")
    if not bug.repaired:
        raise ValueError(f"bug_report {bug_id} has not been repaired yet")

    reporter = get_user_by_id(db, bug.reporter_id)
    username = reporter.username if reporter else f"user#{bug.reporter_id}"

    bug.verified = 1
    save_bug_report(db, bug)
    
    # Add to bug.md repaired section if not already there
    _append_to_repaired_bug_md(
        date_str=datetime.utcnow().strftime("%Y-%m-%d"),
        username=username,
        body=bug.body,
        project="Unknown",
        fix_content="管理员已确认修复"
    )
    
    return _format_bug(bug, username)


def reopen_bug(db: Session, bug_id: int) -> dict:
    """Reopen a bug that was marked as repaired but still has issues."""
    bug = get_bug_report(db, bug_id)
    if not bug:
        raise ValueError(f"bug_report {bug_id} not found")
    if bug.status != "approved":
        raise ValueError(f"bug_report {bug_id} is not approved (status={bug.status})")

    reporter = get_user_by_id(db, bug.reporter_id)
    username = reporter.username if reporter else f"user#{bug.reporter_id}"

    # Reset repair status to allow another repair cycle.
    bug.repaired = 0
    bug.verified = 0
    
    # Remove from bug.md repaired section by moving it back to pending section
    _remove_from_repaired_bug_md(bug.body)
    
    save_bug_report(db, bug)
    return _format_bug(bug, username)


# ── internal helpers ────────────────────────────────────────────────────────

def _format_bug(bug: BugReport, username: str) -> dict:
    return {
        "id": bug.id,
        "reporter": username,
        "body": bug.body,
        "status": bug.status,
        "created_at": bug.created_at.strftime("%Y-%m-%d %H:%M") if bug.created_at else "",
        "approved_at": bug.approved_at.strftime("%Y-%m-%d %H:%M") if bug.approved_at else None,
    }


def _parse_repaired_bugs() -> set[str]:
    """Parse bug.md and return set of bug bodies that are in '已修复 Bug' section."""
    if not _BUG_MD_PATH.exists():
        return set()
    
    content = _BUG_MD_PATH.read_text(encoding="utf-8")
    
    # Find the "已修复 Bug" section
    repaired_section_match = re.search(r'## 已修复 Bug\s+(.+?)(?=## |$)', content, re.DOTALL)
    if not repaired_section_match:
        return set()
    
    repaired_section = repaired_section_match.group(1)
    repaired_bodies = set()
    
    # Extract bug bodies from repaired section
    # Pattern: **描述**: text
    body_pattern = r'\*\*描述\*\*:\s*(.+?)(?=\*\*修复时间\*\*|$)'
    for match in re.finditer(body_pattern, repaired_section, re.DOTALL):
        body = match.group(1).strip()
        if body:
            repaired_bodies.add(body)
    
    return repaired_bodies


def _append_to_bug_md(date_str: str, username: str, body: str) -> None:
    """Append an approved bug entry to Benbot/bug.md."""
    _BUG_MD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Ensure file has a header on first creation
    if not _BUG_MD_PATH.exists():
        header = "# Bug 收录记录\n\n记录经管理员审核通过的 Bug 反馈。\n\n"
        _BUG_MD_PATH.write_text(header, encoding="utf-8")

    entry = f"\n## [{date_str}] 提交者：{username}\n\n{body}\n\n---\n"
    with _BUG_MD_PATH.open("a", encoding="utf-8") as f:
        f.write(entry)


def _append_to_repaired_bug_md(date_str: str, username: str, body: str, project: str, fix_content: str) -> None:
    """Append a verified bug entry to the '已修复 Bug' section in bug.md."""
    _BUG_MD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Ensure file has a header on first creation
    if not _BUG_MD_PATH.exists():
        header = "# Bug 收录记录\n\n记录经管理员审核通过的 Bug 反馈。\n\n## 已修复 Bug\n\n"
        _BUG_MD_PATH.write_text(header, encoding="utf-8")
    
    content = _BUG_MD_PATH.read_text(encoding="utf-8")
    
    # Check if "已修复 Bug" section exists
    if "## 已修复 Bug" not in content:
        # Add the section before the first entry
        content = content.rstrip() + "\n\n## 已修复 Bug\n\n"
    
    # Create the entry
    entry = f"\n### [{date_str}] 提交者：{username}\n**状态**: completed ✅\n**项目**: {project}\n**描述**: {body}\n**修复时间**: {date_str}\n**修复内容**: {fix_content}\n\n---\n"
    
    # Find the position after "## 已修复 Bug" header
    repaired_section_match = re.search(r'(## 已修复 Bug\s*)', content)
    if repaired_section_match:
        insert_pos = repaired_section_match.end(1)
        new_content = content[:insert_pos] + entry + content[insert_pos:]
    else:
        new_content = content + entry
    
    _BUG_MD_PATH.write_text(new_content, encoding="utf-8")


def _remove_from_repaired_bug_md(bug_body: str) -> None:
    """Remove a bug entry from the '已修复 Bug' section in bug.md."""
    if not _BUG_MD_PATH.exists():
        return
    
    content = _BUG_MD_PATH.read_text(encoding="utf-8")
    
    # Find the "已修复 Bug" section
    repaired_section_match = re.search(r'(## 已修复 Bug\s+)(.+?)(?=## |$)', content, re.DOTALL)
    if not repaired_section_match:
        return
    
    repaired_section = repaired_section_match.group(2)
    
    # Find the entry for this bug (look for the body text)
    # We need to find the entire entry block and remove it
    # Entry format: ### [date] 提交者：username\n\n**状态**: completed ✅\n...**描述**: body\n...---\n
    lines = repaired_section.split('\n')
    new_lines = []
    skip_until_separator = False
    
    for i, line in enumerate(lines):
        if skip_until_separator:
            if line.strip() == '---':
                skip_until_separator = False
            continue
        
        # Check if this line starts a bug entry that contains our body
        if line.startswith('### '):
            # Look ahead for the body
            entry_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip() != '---':
                entry_lines.append(lines[j])
                j += 1
            
            entry_text = '\n'.join(entry_lines)
            if bug_body.strip() in entry_text:
                # Skip this entire entry
                skip_until_separator = True
                continue
        
        if not skip_until_separator:
            new_lines.append(line)
    
    # Rebuild the content
    new_repaired_section = '\n'.join(new_lines)
    
    # Replace the old section with the new one
    new_content = content[:repaired_section_match.start(2)] + new_repaired_section + content[repaired_section_match.end(2):]
    
    _BUG_MD_PATH.write_text(new_content, encoding="utf-8")
