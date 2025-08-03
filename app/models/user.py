from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    is_premium: bool = Field(default=False)
    is_admin: bool = Field(default=False)
    board: str = Field(...)
    class_name: str = Field(...)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    is_verified: bool = False
    is_premium: bool = False
    is_admin: bool = False
    board: str
    class_name: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefresh(BaseModel):
    refresh_token: str

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)

class UserStats(BaseModel):
    total_notes: int
    total_questions: int
    subjects_studied: int
    questions_this_week: int
    weak_areas: list[str]
    strong_areas: list[str]
