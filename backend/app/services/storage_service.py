import os
import re
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from backend.app.config import settings

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and illegal characters."""
    base = os.path.basename(filename)
    # Remove null bytes and non-printable characters
    base = re.sub(r'[\x00-\x1f\x7f]', '', base)
    # Replace dangerous characters with underscores
    clean = re.sub(r'[^\w\.\-\_]', '_', base)
    clean = clean.strip('. ')
    return clean or "unnamed_document"

class BaseStorageService(ABC):
    @abstractmethod
    def save_file(self, project_id: str, document_id: str, filename: str, content: bytes) -> Tuple[str, str]:
        """Saves file bytes and returns (storage_key, absolute_path)."""
        pass

    @abstractmethod
    def get_file(self, storage_key: str) -> bytes:
        """Reads and returns file bytes by storage key."""
        pass

    @abstractmethod
    def get_file_path(self, storage_key: str) -> str:
        """Returns the local filesystem path for parsers."""
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Deletes file from storage."""
        pass

    @abstractmethod
    def file_exists(self, storage_key: str) -> bool:
        """Checks if file exists in storage."""
        pass

class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.UPLOAD_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> str:
        """Safely resolves storage key to an absolute path inside base_dir, preventing traversal."""
        # Normalize slashes
        clean_key = storage_key.replace('\\', '/').lstrip('/')
        # Reject keys containing '..'
        parts = clean_key.split('/')
        if '..' in parts:
            raise ValueError("Path traversal attempt detected in storage key.")

        resolved = os.path.abspath(os.path.join(self.base_dir, *parts))
        if not resolved.startswith(self.base_dir):
            raise ValueError("Path traversal attempt detected.")
        return resolved

    def save_file(self, project_id: str, document_id: str, filename: str, content: bytes) -> Tuple[str, str]:
        safe_fname = sanitize_filename(filename)
        # Structured key: projects/{project_id}/documents/{document_id}/{filename}
        storage_key = f"projects/{project_id}/documents/{document_id}/{safe_fname}"
        abs_path = self._resolve_path(storage_key)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(content)

        return storage_key, abs_path

    def get_file(self, storage_key: str) -> bytes:
        abs_path = self._resolve_path(storage_key)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Storage file not found: {storage_key}")
        with open(abs_path, "rb") as f:
            return f.read()

    def get_file_path(self, storage_key: str) -> str:
        abs_path = self._resolve_path(storage_key)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Storage file not found: {storage_key}")
        return abs_path

    def delete_file(self, storage_key: str) -> bool:
        try:
            abs_path = self._resolve_path(storage_key)
            if os.path.exists(abs_path):
                os.remove(abs_path)
                # Attempt to clean empty parent directory
                parent = os.path.dirname(abs_path)
                if os.path.exists(parent) and not os.listdir(parent):
                    os.rmdir(parent)
                return True
            return False
        except Exception:
            return False

    def file_exists(self, storage_key: str) -> bool:
        try:
            abs_path = self._resolve_path(storage_key)
            return os.path.exists(abs_path)
        except Exception:
            return False

# Global instance
storage_service = LocalStorageService()
