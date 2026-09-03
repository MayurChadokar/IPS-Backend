import os
import io
import uuid
import re
import shutil
from typing import BinaryIO, Union
from PIL import Image
from app.core.config import settings

UPLOAD_DIR = os.path.join(os.getcwd(), getattr(settings, "UPLOAD_DIR", "uploads"))


def process_image_to_webp(file_obj: BinaryIO, quality: int = 85) -> io.BytesIO:
    """
    Process an image: convert to WebP format and compress
    """
    try:
        img = Image.open(file_obj)
        
        # Convert RGBA to RGB if necessary (WebP supports both, but RGB is smaller)
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality, method=6)
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"Image processing error: {e}")
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        return file_obj


def upload_image(file_path_or_obj: Union[str, BinaryIO], folder: str = "ips_cms", 
                 convert_to_webp: bool = True, quality: int = 85, filename: str = None,
                 resource_type: str = "image") -> str:
    """
    Upload an image or file to the local server's `uploads/` directory with the matching folder structure.
    
    Target Path: uploads/{folder}/{filename}
    Returns URL: /uploads/{folder}/{filename}
    """
    try:
        # Determine raw filename
        raw_name = filename
        if not raw_name and hasattr(file_path_or_obj, 'name') and file_path_or_obj.name:
            raw_name = os.path.basename(str(file_path_or_obj.name))
        
        if not raw_name:
            raw_name = f"file_{uuid.uuid4().hex[:8]}.bin"

        # Separate base name and extension
        base_name, ext = os.path.splitext(raw_name)
        ext = ext.lower()
        clean_base = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
        if not clean_base:
            clean_base = "file"
        
        # Ensure file position is at the start
        if hasattr(file_path_or_obj, 'seek'):
            file_path_or_obj.seek(0)

        # File type checks
        is_svg = ext == '.svg'
        is_video = ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv']
        is_document = ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.zip', '.rar']
        is_skip_conversion = ext in ['.svg', '.ico', '.gif']

        # Determine target directory
        clean_folder = folder.strip("/\\")
        target_dir = os.path.join(UPLOAD_DIR, clean_folder)
        os.makedirs(target_dir, exist_ok=True)

        # Handle WebP conversion for standard images
        if convert_to_webp and not (is_svg or is_video or is_document or is_skip_conversion):
            try:
                processed_stream = process_image_to_webp(file_path_or_obj, quality=quality)
                if isinstance(processed_stream, io.BytesIO):
                    save_name = f"{clean_base}.webp"
                    target_file_path = os.path.join(target_dir, save_name)
                    if os.path.exists(target_file_path):
                        save_name = f"{clean_base}_{uuid.uuid4().hex[:6]}.webp"
                        target_file_path = os.path.join(target_dir, save_name)

                    with open(target_file_path, 'wb') as f:
                        f.write(processed_stream.getvalue())
                    
                    base_url = getattr(settings, "BASE_URL", "").rstrip("/")
                    relative_url = f"{base_url}/uploads/{clean_folder}/{save_name}"
                    print(f"Saved local WebP image: {target_file_path} -> {relative_url}")
                    return relative_url
            except Exception as img_err:
                print(f"WebP conversion failed ({img_err}), saving original file")
                if hasattr(file_path_or_obj, 'seek'):
                    file_path_or_obj.seek(0)

        # Standard file saving (without WebP conversion or fallback)
        save_name = f"{clean_base}{ext}"
        target_file_path = os.path.join(target_dir, save_name)

        if os.path.exists(target_file_path):
            save_name = f"{clean_base}_{uuid.uuid4().hex[:6]}{ext}"
            target_file_path = os.path.join(target_dir, save_name)

        if isinstance(file_path_or_obj, str) and os.path.exists(file_path_or_obj):
            shutil.copy2(file_path_or_obj, target_file_path)
        elif hasattr(file_path_or_obj, 'read'):
            content = file_path_or_obj.read()
            with open(target_file_path, 'wb') as f:
                f.write(content)
        else:
            raise ValueError("Invalid file object or path provided")

        base_url = getattr(settings, "BASE_URL", "").rstrip("/")
        relative_url = f"{base_url}/uploads/{clean_folder}/{save_name}"
        print(f"Saved local file: {target_file_path} -> {relative_url}")
        return relative_url

    except Exception as e:
        print(f"Local upload error: {e}")
        raise e


def delete_image(public_id: str) -> bool:
    """
    Delete a file from local uploads directory
    """
    try:
        if not public_id:
            return False
        clean_path = public_id.lstrip("/")
        if clean_path.startswith("uploads/"):
            file_path = os.path.join(os.getcwd(), clean_path)
        else:
            file_path = os.path.join(UPLOAD_DIR, clean_path)

        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted local file: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Local file delete error: {e}")
        return False


def get_public_id_from_url(url: str) -> str:
    """
    Extract relative uploads path from a URL.
    """
    try:
        if not url:
            return ""
        if "/uploads/" in url:
            return url.split("/uploads/", 1)[1]
        return url
    except Exception as e:
        print(f"get_public_id_from_url error: {e}")
        return url
