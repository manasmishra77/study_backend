from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=100)
    topic: Optional[str] = Field(None, max_length=100)

class NoteResponse(BaseModel):
    id: str
    user_id: str
    title: str
    subject: str
    topic: Optional[str] = None
    image_url: str
    cloudinary_public_id: str
    upload_date: datetime
    file_size: int
    file_type: str
    metadata: dict
    
    class Config:
        from_attributes = True

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = Field(None, min_length=1, max_length=100)
    topic: Optional[str] = Field(None, max_length=100)

class NoteWithQuestions(BaseModel):
    note: NoteResponse
    questions_count: int
    recent_questions: list[str]

class SubjectStats(BaseModel):
    subject: str
    notes_count: int
    questions_count: int
    last_activity: datetime
