import uuid
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


async def save_image(upload: UploadFile, restaurant_id: int, max_width: int = 1200) -> str:
    """Re-encode an uploaded image to WebP and return its media-relative path."""
    raw = await upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Rasm hajmi 5 MB dan oshmasin")

    try:
        with Image.open(BytesIO(raw)) as probe:
            image_format = probe.format
            probe.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fayl rasm emas")

    if image_format not in ALLOWED_FORMATS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Faqat JPEG, PNG, WEBP yoki GIF")

    with Image.open(BytesIO(raw)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        if image.width > max_width:
            height = round(image.height * max_width / image.width)
            image = image.resize((max_width, height), Image.LANCZOS)

        directory = settings.media_path / str(restaurant_id)
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.webp"
        image.save(directory / filename, "WEBP", quality=82, method=4)

    return f"{restaurant_id}/{filename}"


def delete_image(relative_path: str | None) -> None:
    if not relative_path:
        return
    target = (settings.media_path / relative_path).resolve()
    if not target.is_relative_to(settings.media_path.resolve()):
        return
    target.unlink(missing_ok=True)
