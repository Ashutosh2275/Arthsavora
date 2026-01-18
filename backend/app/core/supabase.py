from supabase import create_client, Client
from .config import settings
import uuid

# Initialize Supabase client
supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def upload_receipt_to_supabase(file_bytes: bytes, original_name: str):
    """
    Uploads a receipt image to the 'receipts' bucket and returns the public URL.
    """
    try:
        # Generate a unique filename to avoid overwrites
        ext = original_name.split('.')[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"
        
        # Upload to the 'receipts' bucket
        supabase_client.storage.from_("receipts").upload(
            path=unique_name,
            file=file_bytes,
            file_options={"content-type": f"image/{ext}"}
        )
        
        # Get the public URL for the uploaded file
        public_url = supabase_client.storage.from_("receipts").get_public_url(unique_name)
        return public_url
    except Exception as e:
        print(f"Supabase Storage Error: {e}")
        return None