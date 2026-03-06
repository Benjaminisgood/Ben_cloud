"""代码备份服务 - 在修复前备份相关文件"""
from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# Benbot root directory
_BENBOT_ROOT = Path(__file__).resolve().parents[5]
_BACKUP_DIR = _BENBOT_ROOT / "backups"


def create_backup(files_to_backup: list[str], bug_id: int = None, description: str = "") -> str:
    """
    Create a zip backup of specified files.
    
    Args:
        files_to_backup: List of file paths to backup
        bug_id: Optional bug ID for naming
        description: Optional description for the backup
    
    Returns:
        Path to the created backup zip file
    """
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bug_suffix = f"_bug{bug_id}" if bug_id else ""
    backup_name = f"backup_{timestamp}{bug_suffix}.zip"
    backup_path = _BACKUP_DIR / backup_name
    
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files_to_backup:
            file = Path(file_path)
            if file.exists():
                # Store with relative path from Benbot root
                try:
                    arcname = file.relative_to(_BENBOT_ROOT)
                except ValueError:
                    # File is outside Benbot root, use absolute path
                    arcname = file
                zipf.write(file, arcname)
    
    return str(backup_path)


def backup_project_files(bug_body: str) -> tuple[str, list[str]]:
    """
    Analyze bug description and backup relevant project files.
    
    Args:
        bug_body: The bug description text
    
    Returns:
        Tuple of (backup_path, list_of_backed_up_files)
    """
    files_to_backup = []
    
    # Default: backup key configuration and source files
    # Parse bug body to identify affected files/projects
    bug_lower = bug_body.lower()
    
    # Benusy project files
    if 'benusy' in bug_lower:
        files_to_backup.extend([
            _BENBOT_ROOT / "apps" / "api" / "src" / "benbot_api" / "core" / "config.py",
            _BENBOT_ROOT / "apps" / "web" / "templates" / "benusy",
        ])
    
    # Bensci project files
    if 'bensci' in bug_lower or 'metadata' in bug_lower:
        files_to_backup.extend([
            _BENBOT_ROOT / "apps" / "api" / "src" / "benbot_api" / "core" / "config.py",
        ])
    
    # Benome project files
    if 'benome' in bug_lower:
        files_to_backup.extend([
            _BENBOT_ROOT / "apps" / "api" / "src" / "benbot_api" / "core" / "config.py",
        ])
    
    # Generic: always backup config and main files
    core_files = [
        _BENBOT_ROOT / "apps" / "api" / "src" / "benbot_api" / "core" / "config.py",
        _BENBOT_ROOT / "apps" / "api" / "src" / "benbot_api" / "main.py",
        _BENBOT_ROOT / ".env",
    ]
    
    for f in core_files:
        if f.exists() and str(f) not in [str(x) for x in files_to_backup]:
            files_to_backup.append(f)
    
    # Filter to only existing files
    existing_files = [str(f) for f in files_to_backup if Path(f).exists()]
    
    if not existing_files:
        # Fallback: backup entire apps directory structure (not contents)
        existing_files = [str(_BENBOT_ROOT / "apps" / "api" / "src" / "benbot_api" / "core" / "config.py")]
    
    backup_path = create_backup(existing_files, description=bug_body[:50])
    
    return backup_path, existing_files


def get_backup_history() -> list[dict]:
    """List all backups in chronological order."""
    if not _BACKUP_DIR.exists():
        return []
    
    backups = []
    for zip_file in sorted(_BACKUP_DIR.glob("backup_*.zip")):
        stat = zip_file.stat()
        backups.append({
            "filename": zip_file.name,
            "path": str(zip_file),
            "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "size_bytes": stat.st_size,
        })
    
    return backups
