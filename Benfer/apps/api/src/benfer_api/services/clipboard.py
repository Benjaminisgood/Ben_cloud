import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from benfer_api.core.config import get_settings

settings = get_settings()


class ClipboardService:
    def __init__(self):
        self.storage_path = Path(settings.clipboard_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def generate_access_token(self) -> str:
        """Generate unique access token"""
        return str(uuid.uuid4())

    def save_clipboard(self, content: str, content_type: str, 
                       expires_in_hours: Optional[int] = None) -> tuple[str, datetime]:
        """Save clipboard content to local storage"""
        access_token = self.generate_access_token()
        
        # Calculate expiration
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        else:
            expires_at = datetime.utcnow() + timedelta(hours=settings.FILE_EXPIRATION_HOURS)
        
        # Save to file
        file_path = self.storage_path / f"{access_token}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return access_token, expires_at

    def get_clipboard(self, access_token: str) -> Optional[str]:
        """Get clipboard content by access token"""
        file_path = self.storage_path / f"{access_token}.txt"
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def delete_clipboard(self, access_token: str) -> bool:
        """Delete clipboard content"""
        file_path = self.storage_path / f"{access_token}.txt"
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired clipboard files"""
        count = 0
        now = datetime.utcnow()
        
        for file_path in self.storage_path.glob("*.txt"):
            # Check file modification time
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if now - mtime > timedelta(hours=settings.FILE_EXPIRATION_HOURS):
                file_path.unlink()
                count += 1
        
        return count


def get_clipboard_service() -> ClipboardService:
    return ClipboardService()
