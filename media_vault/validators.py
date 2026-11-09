import hashlib
from PIL import Image
from rest_framework.exceptions import ValidationError

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/webm', 'video/quicktime'}
ALLOWED_MIME_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES

MAX_IMAGE_SIZE = 15 * 1024 * 1024   # 15 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB

def calculate_sha256(file_obj) -> str:
    hasher = hashlib.sha256()
    file_obj.seek(0)
    while chunk := file_obj.read(64 * 1024):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()

def validate_media_file(file_obj):
    filename = getattr(file_obj, 'name', 'unnamed')
    content_type = getattr(file_obj, 'content_type', '').lower()
    size = getattr(file_obj, 'size', 0)

    # Basic content type inspection
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported file format '{content_type}'. Allowed types: JPG, PNG, WEBP, GIF, MP4, WEBM."
        )

    # Size validations
    if content_type in ALLOWED_IMAGE_TYPES and size > MAX_IMAGE_SIZE:
        raise ValidationError(f"Image file exceeds maximum limit of {MAX_IMAGE_SIZE // (1024 * 1024)} MB.")

    if content_type in ALLOWED_VIDEO_TYPES and size > MAX_VIDEO_SIZE:
        raise ValidationError(f"Video file exceeds maximum limit of {MAX_VIDEO_SIZE // (1024 * 1024)} MB.")

    width, height = None, None
    file_type = 'VIDEO'

    if content_type in ALLOWED_IMAGE_TYPES:
        file_type = 'IMAGE'
        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            img.verify()
            width, height = img.size
            file_obj.seek(0)
        except Exception as e:
            raise ValidationError("Corrupt or invalid image file.") from e

    return {
        'file_type': file_type,
        'mime_type': content_type,
        'file_size': size,
        'width': width,
        'height': height,
    }

