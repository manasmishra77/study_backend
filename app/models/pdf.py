from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class PDFUploadResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    file_path: str
    subject: str
    description: Optional[str] = None
    upload_date: datetime
    status: str  # "uploaded", "processing", "processed", "failed"
    metadata: dict
    
    class Config:
        from_attributes = True

class PDFProcessingStatus(BaseModel):
    id: str
    status: str
    progress_percentage: int
    message: str
    processed_at: Optional[datetime] = None

class PDFListResponse(BaseModel):
    pdfs: List[PDFUploadResponse]
    total_count: int
    total_size_bytes: int