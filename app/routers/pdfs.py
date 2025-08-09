from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from datetime import datetime
from typing import List, Optional
import tempfile
import os
import logging

from app.models.pdf import PDFUploadResponse, PDFListResponse
from app.utils.database import get_database, get_object_id, serialize_object_id
from app.utils.cloudinary_utils import upload_pdf_to_cloudinary, delete_pdf_from_cloudinary
from app.study_agent.rag_utils import RAGManager
from app.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdfs", tags=["PDFs"])

@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    subject: str = Form(...),
    class_name: str = Form(...),
    chapter: str = Form(...),
    board: str = Form(...),
    topics: List[str] = Form([]),
    description: Optional[str] = Form(None)
):
    """Upload a PDF file to Cloudinary and store metadata."""
    db = get_database()
    
    logger.info(f"Received PDF upload: {file.filename}, Subject: {subject}")
    
    # Validate file type
    if not file.content_type == "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    # Validate file size (limit to 50MB)
    file_content = await file.read()
    logger.info(f"File size: {len(file_content)} bytes")
    
    if len(file_content) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size must be less than 50MB"
        )
    
    # Reset file position for Cloudinary upload
    await file.seek(0)
    
    # Create temporary file for RAG processing
    temp_pdf_path = None
    try:
        logger.info("Creating temporary file...")
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_pdf_path = temp_file.name
            temp_file.write(file_content)
        
        logger.info(f"Temporary file created: {temp_pdf_path}")
        
        # Process with RAG manager using the temporary file path
        logger.info("Initializing RAG manager...")
        rag_manager = RAGManager(api_key=settings.google_api_key)
        
        logger.info("Loading PDF with board info...")
        rag_manager.load_pdf_with_board(
            pdf_path=temp_pdf_path, 
            subject=subject,
            class_name=class_name, 
            chapter=chapter, 
            board=board,
            topics=topics
        )
        
        # Reset file position again for Cloudinary upload
        await file.seek(0)
        
        logger.info("Uploading to Cloudinary...")
        # Upload to Cloudinary
        upload_result = await upload_pdf_to_cloudinary(file, folder="rag_pdfs")
        
        logger.info("Creating database record...")
        # Create PDF document in database
        pdf_data = {
            "filename": upload_result["original_filename"],
            "original_filename": file.filename,
            "file_size": upload_result["bytes"],
            "file_path": upload_result["url"],  # Cloudinary URL
            "cloudinary_public_id": upload_result["public_id"],
            "subject": subject,
            "description": description,
            "class_name": class_name,
            "chapter": chapter,
            "board": board,
            "upload_date": datetime.utcnow(),
            "status": "uploaded",
            "metadata": {
                "content_type": file.content_type,
                "cloudinary_format": upload_result["format"],
                "cloudinary_created_at": upload_result["created_at"]
            }
        }
        
        result = await db.rag_pdfs.insert_one(pdf_data)
        pdf_data["_id"] = result.inserted_id
        
        logger.info(f"PDF upload completed successfully: {pdf_data['_id']}")
        return serialize_object_id(pdf_data)
    
    except Exception as e:
        logger.error(f"Error during PDF upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload PDF: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
                logger.info(f"Cleaned up temporary file: {temp_pdf_path}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_pdf_path}: {e}")

@router.get("", response_model=PDFListResponse)
async def get_all_pdfs():
    """Get all uploaded PDFs."""
    db = get_database()
    
    # Get all PDFs
    pdfs_cursor = db.rag_pdfs.find({}).sort("upload_date", -1)
    pdfs = await pdfs_cursor.to_list(None)
    
    # Calculate statistics
    total_count = len(pdfs)
    total_size_bytes = sum(pdf.get("file_size", 0) for pdf in pdfs)
    
    # Serialize PDFs
    serialized_pdfs = [serialize_object_id(pdf) for pdf in pdfs]
    
    return PDFListResponse(
        pdfs=serialized_pdfs,
        total_count=total_count,
        total_size_bytes=total_size_bytes
    )

@router.get("/{pdf_id}", response_model=PDFUploadResponse)
async def get_pdf_by_id(pdf_id: str):
    """Get a specific PDF by ID."""
    db = get_database()
    
    # Find PDF
    pdf = await db.rag_pdfs.find_one({"_id": get_object_id(pdf_id)})
    
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    return serialize_object_id(pdf)

@router.delete("/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """Delete a PDF from Cloudinary and database."""
    db = get_database()
    
    # Find PDF
    pdf = await db.rag_pdfs.find_one({"_id": get_object_id(pdf_id)})
    
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    try:
        # Delete from Cloudinary
        cloudinary_public_id = pdf.get("cloudinary_public_id")
        if cloudinary_public_id:
            await delete_pdf_from_cloudinary(cloudinary_public_id)
        
        # Delete from database
        await db.rag_pdfs.delete_one({"_id": get_object_id(pdf_id)})
        
        return {"message": "PDF deleted successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete PDF: {str(e)}"
        )