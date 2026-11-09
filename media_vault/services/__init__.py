from .base import (
    BaseStorageService,
    StorageException,
    StorageFileNotFoundException,
    StorageAuthenticationException
)
from .local_driver import LocalStorageDriver
from .gdrive_driver import GoogleDriveStorageDriver
from django.conf import settings

def get_storage_service(provider: str = None) -> BaseStorageService:
    if not provider:
        provider = getattr(settings, 'STORAGE_DRIVER', 'local').lower()
    if provider == 'gdrive':
        return GoogleDriveStorageDriver()
    return LocalStorageDriver()
