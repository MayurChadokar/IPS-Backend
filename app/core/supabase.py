import httpx
import uuid
from typing import BinaryIO, Union
from app.core.config import settings

def upload_pdf_to_supabase(file_obj: BinaryIO, folder: str = "journals", filename: str = None) -> str:
    """
    Uploads a PDF file directly to Supabase storage bucket.
    
    Args:
        file_obj: File-like object (binary)
        folder: Folder path within the bucket
        filename: Original name of the file
        
    Returns:
        The public URL of the uploaded file on Supabase.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured in environment variables.")

    # Generate a safe, unique filename if not provided
    if not filename:
        filename = f"{uuid.uuid4().hex}.pdf"
    else:
        # Prepend a UUID to avoid conflicts in Supabase Storage
        filename = f"{uuid.uuid4().hex}_{filename}"

    # Ensure URL formatting is correct
    supabase_url = settings.SUPABASE_URL.rstrip('/')
    bucket = settings.SUPABASE_BUCKET or "journals"
    
    # Target path inside the bucket
    target_path = f"{folder}/{filename}".strip('/')
    
    # Supabase REST endpoint for file upload
    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{target_path}"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/pdf",
        "x-upsert": "true"
    }

    # Ensure file pointer is at the beginning
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
        
    file_data = file_obj.read()

    print(f"Uploading file to Supabase: {upload_url}...")
    
    # Perform upload synchronously
    with httpx.Client() as client:
        response = client.post(upload_url, headers=headers, content=file_data)
        
        if response.status_code != 200:
            print(f"Supabase upload failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to upload to Supabase: {response.text}")
            
    # Construct and return the public URL
    # Format: https://{project_id}.supabase.co/storage/v1/object/public/{bucket}/{path}
    public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{target_path}"
    print(f"Supabase upload successful! Public URL: {public_url}")
    return public_url
