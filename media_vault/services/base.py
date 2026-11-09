from abc import ABC, abstractmethod
from typing import Tuple, Generator, BinaryIO, Optional, Dict, Any

class StorageException(Exception):
    """Base exception for storage errors."""
    pass


class StorageFileNotFoundException(StorageException):
    """Raised when the requested file does not exist in the storage provider."""
    pass


class StorageAuthenticationException(StorageException):
    """Raised when authentication to the storage provider fails."""
    pass


class BaseStorageService(ABC):
    """
    Abstract interface for media storage backends.
    Decouples application models (Posts, Employees) from the physical storage provider
    (Local Disk, Google Drive, AWS S3, etc.).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the unique identifier of the storage provider (e.g. 'local', 'gdrive')."""
        pass

    @abstractmethod
    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int
    ) -> Dict[str, Any]:
        """
        Uploads a file to the storage provider.
        Returns a dictionary containing at least:
        - 'storage_file_id': unique file identifier for future retrieval
        - 'provider': provider name
        - 'file_size': size in bytes
        """
        pass

    @abstractmethod
    def get_file_stream(self, storage_file_id: str) -> Tuple[Generator[bytes, None, None], str, int]:
        """
        Retrieves a streaming generator for the file content.
        Returns: (stream_generator, content_type, content_length)
        """
        pass

    @abstractmethod
    def delete_file(self, storage_file_id: str) -> bool:
        """
        Deletes a file from the storage provider.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def file_exists(self, storage_file_id: str) -> bool:
        """
        Checks whether the file exists in the storage provider.
        """
        pass

