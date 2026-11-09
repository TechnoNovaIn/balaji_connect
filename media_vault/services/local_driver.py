import os
import uuid
import mimetypes
from pathlib import Path
from typing import Tuple, Generator, BinaryIO, Dict, Any
from django.conf import settings
from .base import BaseStorageService, StorageFileNotFoundException, StorageException

class LocalStorageDriver(BaseStorageService):
    """
    Local filesystem storage driver.
    Ideal for local development, automated testing, and isolated staging environments.
    """

    def __init__(self, base_dir: Path = None):
        self.base_dir = Path(base_dir or getattr(settings, 'LOCAL_STORAGE_DIR', settings.BASE_DIR / 'media_vault_storage'))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return 'local'

    def _get_path(self, storage_file_id: str) -> Path:
        # Sanitize storage_file_id against directory traversal
        clean_name = os.path.basename(storage_file_id)
        return self.base_dir / clean_name

    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int
    ) -> Dict[str, Any]:
        ext = Path(filename).suffix
        unique_file_id = f"{uuid.uuid4().hex}{ext}"
        target_path = self._get_path(unique_file_id)

        try:
            file_obj.seek(0)
            bytes_written = 0
            with open(target_path, 'wb') as dest:
                while chunk := file_obj.read(64 * 1024):
                    dest.write(chunk)
                    bytes_written += len(chunk)

            return {
                'storage_file_id': unique_file_id,
                'provider': self.provider_name,
                'file_size': bytes_written,
                'content_type': content_type,
            }
        except Exception as e:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise StorageException(f"Failed to save local file: {str(e)}") from e

    def get_file_stream(self, storage_file_id: str) -> Tuple[Generator[bytes, None, None], str, int]:
        target_path = self._get_path(storage_file_id)
        if not target_path.exists() or not target_path.is_file():
            raise StorageFileNotFoundException(f"File {storage_file_id} not found on local disk.")

        content_size = target_path.stat().st_size
        guessed_type, _ = mimetypes.guess_type(str(target_path))
        content_type = guessed_type or 'application/octet-stream'

        def chunk_generator(chunk_size=64 * 1024):
            with open(target_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    yield chunk

        return chunk_generator(), content_type, content_size

    def delete_file(self, storage_file_id: str) -> bool:
        target_path = self._get_path(storage_file_id)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def file_exists(self, storage_file_id: str) -> bool:
        target_path = self._get_path(storage_file_id)
        return target_path.exists() and target_path.is_file()

