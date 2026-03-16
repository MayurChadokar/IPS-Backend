import cloudinary
import cloudinary.uploader
from app.core.config import settings
from PIL import Image
import io
from typing import BinaryIO, Union

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

def process_image_to_webp(file_obj: BinaryIO, quality: int = 85) -> io.BytesIO:
    """
    Process an image: convert to WebP format and compress
    
    Args:
        file_obj: File object or file-like object
        quality: WebP quality (1-100, default 85 for good balance)
    
    Returns:
        BytesIO object containing the processed WebP image
    """
    try:
        # Open the image
        img = Image.open(file_obj)
        
        # Convert RGBA to RGB if necessary (WebP supports both, but RGB is smaller)
        if img.mode == 'RGBA':
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as WebP to BytesIO (keeping original dimensions)
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality, method=6)  # method=6 for best compression
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"Image processing error: {e}")
        # If processing fails, return original file
        file_obj.seek(0)
        return file_obj


def upload_image(file_path_or_obj: Union[str, BinaryIO], folder: str = "ips_cms", 
                 convert_to_webp: bool = True, quality: int = 85, filename: str = None,
                 resource_type: str = "image") -> str:
    """
    Upload an image or file to Cloudinary with automatic WebP conversion
    
    Args:
        file_path_or_obj: File path string or file-like object
        folder: Cloudinary folder name
        convert_to_webp: Whether to convert images to WebP (default True)
        quality: WebP quality for conversion (1-100, default 85)
        filename: Optional filename to determine file type
        resource_type: Cloudinary resource type ("image", "video", "auto", "raw")
    
    Returns:
        Secure URL of the uploaded file
    
    Raises:
        Exception: If upload fails
    """
    try:
        # Determine file extension from filename
        ext = None
        if filename and isinstance(filename, str) and '.' in filename:
            ext = filename.lower().rsplit('.', 1)[-1]
        elif hasattr(file_path_or_obj, 'name') and file_path_or_obj.name and '.' in str(file_path_or_obj.name):
            ext = str(file_path_or_obj.name).lower().rsplit('.', 1)[-1]
        
        is_svg = ext == 'svg'
        is_video = ext in ['mp4', 'webm', 'mov', 'avi', 'mkv', 'flv', 'wmv']
        # ICO and JFIF should skip WebP conversion but upload as image
        is_skip_conversion = ext in ['svg', 'ico', 'gif']
        
        # Ensure file is at the beginning
        if hasattr(file_path_or_obj, 'seek'):
            file_path_or_obj.seek(0)
        
        # SVG files: upload as raw so Cloudinary preserves the SVG format
        if is_svg:
            print(f"Uploading SVG file as-is (raw)...")
            response = cloudinary.uploader.upload(
                file_path_or_obj,
                folder=folder,
                resource_type="raw",
                format="svg"
            )
            return response.get("secure_url")
        
        # Video files: upload with resource_type="video"
        if is_video:
            print(f"Uploading video file ({ext})...")
            response = cloudinary.uploader.upload(
                file_path_or_obj,
                folder=folder,
                resource_type="video"
            )
            return response.get("secure_url")
        
        # Files that should skip WebP conversion (ICO, GIF, etc.)
        if is_skip_conversion:
            print(f"Uploading {ext} file without conversion...")
            response = cloudinary.uploader.upload(
                file_path_or_obj,
                folder=folder,
                resource_type=resource_type
            )
            return response.get("secure_url")
        
        # Standard image files: try WebP conversion
        if hasattr(file_path_or_obj, 'read') and convert_to_webp:
            try:
                current_pos = file_path_or_obj.tell() if hasattr(file_path_or_obj, 'tell') else 0
                
                test_img = Image.open(file_path_or_obj)
                file_path_or_obj.seek(current_pos)
                
                if test_img.format == 'WEBP':
                    print("Image is already in WebP format, uploading as-is")
                    processed_file = file_path_or_obj
                else:
                    print(f"Converting {test_img.format} image to WebP...")
                    file_path_or_obj.seek(current_pos)
                    processed_file = process_image_to_webp(file_path_or_obj, quality=quality)
                
                response = cloudinary.uploader.upload(
                    processed_file,
                    folder=folder,
                    resource_type=resource_type,
                    format="webp"
                )
            except Exception as img_error:
                # Processing failed — upload as-is with auto resource type detection
                print(f"Image processing failed ({img_error}), uploading as-is with auto detection")
                file_path_or_obj.seek(0)
                response = cloudinary.uploader.upload(
                    file_path_or_obj,
                    folder=folder,
                    resource_type="auto"
                )
        else:
            # No conversion requested or not a file object
            response = cloudinary.uploader.upload(
                file_path_or_obj,
                folder=folder,
                resource_type=resource_type
            )
        
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        raise e


def delete_image(public_id: str) -> bool:
    """
    Delete an image from Cloudinary
    
    Args:
        public_id: The public ID of the image to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        cloudinary.uploader.destroy(public_id)
        return True
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
        return False


def get_public_id_from_url(url: str) -> str:
    """
    Extract Cloudinary public_id from a secure URL.

    Example URL formats:
    - https://res.cloudinary.com/<cloud>/image/upload/v123456/folder/name.webp
    - https://res.cloudinary.com/<cloud>/image/upload/folder/name.webp

    This returns 'folder/name' (without extension or version prefix).
    """
    try:
        # Remove protocol and domain
        parts = url.split('/')
        # Find 'upload' segment index
        if 'upload' in parts:
            idx = parts.index('upload')
        else:
            # fallback: last 3 segments
            idx = len(parts) - 3

        # The public id and possible folders are after the upload segment and optional version
        tail = parts[idx+1:]
        # If first tail segment starts with 'v' followed by digits, skip it
        if tail and tail[0].startswith('v') and tail[0][1:].isdigit():
            tail = tail[1:]

        if not tail:
            return ''

        # Join remaining and strip extension
        last = '/'.join(tail)
        # remove query params
        last = last.split('?')[0]
        # strip extension
        if '.' in last:
            last = last.rsplit('.', 1)[0]

        return last
    except Exception as e:
        print(f"get_public_id_from_url error: {e}")
        return ''
