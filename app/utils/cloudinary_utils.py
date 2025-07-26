import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from PIL import Image
import io
from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret
)

async def upload_image_to_cloudinary(file: UploadFile, folder: str = "personal_tutor") -> dict:
    """Upload image to Cloudinary and return URL and public_id."""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        contents = await file.read()
        
        # Optimize image before upload
        optimized_image = optimize_image(contents)
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            optimized_image,
            folder=folder,
            resource_type="image",
            quality="auto",
            fetch_format="auto"
        )
        
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result["width"],
            "height": result["height"],
            "format": result["format"],
            "bytes": result["bytes"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

async def delete_image_from_cloudinary(public_id: str) -> bool:
    """Delete image from Cloudinary."""
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
    except Exception:
        return False

def optimize_image(image_bytes: bytes, max_size: tuple = (1920, 1080), quality: int = 85) -> bytes:
    """Optimize image size and quality."""
    try:
        # Open image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # Resize if too large
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)
        
        return output.getvalue()
    
    except Exception:
        # Return original if optimization fails
        return image_bytes
