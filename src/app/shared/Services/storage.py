import asyncio
import base64
import io
import os
import uuid
from pathlib import Path
from typing import Optional
from PIL import Image
from fastapi import HTTPException, UploadFile

from src.app.core.config import settings
from src.app.core.logger import app_logger

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def _convert_and_save_webp(raw_bytes: bytes, output_path: Path) -> None:
    with Image.open(io.BytesIO(raw_bytes)) as img:
        # Convert RGBA or other modes appropriately
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(output_path, "WEBP", quality=80)

async def process_image_url(url_or_data: Optional[str]) -> Optional[str]:
    """
    Processes image input:
    - If None or empty, returns empty string or None.
    - If Data URL (data:image/...;base64,...), decodes, converts to WebP, saves to uploads/, returns absolute URL.
    - If standard URL, returns as-is.
    """
    if not url_or_data:
        return url_or_data

    if not url_or_data.startswith("data:image/"):
        return url_or_data

    try:
        header, b64_data = url_or_data.split(",", 1)
        raw_bytes = base64.b64decode(b64_data)
        file_id = f"{uuid.uuid4()}.webp"
        file_path = UPLOAD_DIR / file_id

        # CPU-bound image conversion in worker thread
        await asyncio.to_thread(_convert_and_save_webp, raw_bytes, file_path)

        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/uploads/{file_id}"
    except Exception as e:
        app_logger.error(f"Error converting image to WebP: {e}")
        raise HTTPException(status_code=400, detail="Format gambar tidak valid atau gagal diproses")

async def save_uploaded_file(file: UploadFile) -> str:
    """Saves uploaded multipart file safely and returns filename."""
    ext = Path(file.filename or "file").suffix
    safe_name = f"{uuid.uuid4()}{ext}"
    target_path = UPLOAD_DIR / safe_name
    
    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)
        
    return safe_name

def delete_stored_file(file_name_or_url: Optional[str]) -> None:
    """
    Deletes physical file from uploads folder with strict path traversal protection.
    Accepts full URL or filename.
    """
    if not file_name_or_url:
        return

    # Extract filename if full URL is given
    filename = file_name_or_url.split("/")[-1].split("?")[0]
    
    # Path traversal check: must not contain slashes, backslashes, or '..'
    if "/" in filename or "\\" in filename or ".." in filename:
        app_logger.warning(f"Path traversal attempt detected in file deletion: {filename}")
        return

    file_path = UPLOAD_DIR / filename
    try:
        if file_path.is_file():
            file_path.unlink()
            app_logger.info(f"Deleted file: {file_path}")
    except Exception as e:
        app_logger.error(f"Failed to delete file {file_path}: {e}")
