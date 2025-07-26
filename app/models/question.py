from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class QuestionCreate(BaseModel):
    note_id: str
    question_text: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1, max_length=100)
    topic: Optional[str] = Field(None, max_length=100)
    difficulty_level: str = Field(..., pattern="^(easy|medium|hard)$")
    question_type: str = Field(..., max_length=50)

class QuestionResponse(BaseModel):
    id: str
    user_id: str
    note_id: str
    question_text: str
    subject: str
    topic: Optional[str] = None
    difficulty_level: str
    question_type: str
    created_at: datetime

class QuestionUpdate(BaseModel):
    question_text: Optional[str] = Field(None, min_length=1)
    subject: Optional[str] = Field(None, min_length=1, max_length=100)
    topic: Optional[str] = Field(None, max_length=100)
    difficulty_level: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    question_type: Optional[str] = Field(None, max_length=50)

class FeedbackCreate(BaseModel):
    feedback_text: str = Field(..., min_length=1)
    feedback_type: str = Field(..., max_length=50)

class FeedbackResponse(BaseModel):
    id: str
    question_id: str
    feedback_text: str
    feedback_type: str
    is_ai_generated: bool = False
    created_at: datetime

class FeedbackUpdate(BaseModel):
    feedback_text: Optional[str] = Field(None, min_length=1)
    feedback_type: Optional[str] = Field(None, max_length=50)

class QuestionWithFeedback(BaseModel):
    question: QuestionResponse
    feedback: list[FeedbackResponse]

class QuestionAnalytics(BaseModel):
    total_questions: int
    by_difficulty: dict[str, int]
    by_subject: dict[str, int]
    by_question_type: dict[str, int]
    recent_questions: list[QuestionResponse]

class SuggestedQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1, max_length=100)
    topic: Optional[str] = Field(None, max_length=100)
    difficulty_level: str = Field(..., pattern="^(easy|medium|hard)$")
    based_on_weak_areas: list[str] = Field(default_factory=list)

class SuggestedQuestionResponse(BaseModel):
    id: str
    user_id: str
    question_text: str
    subject: str
    topic: Optional[str] = None
    difficulty_level: str
    based_on_weak_areas: list[str]
    is_completed: bool = False
    suggested_at: datetime
    completed_at: Optional[datetime] = None

class SuggestedQuestionUpdate(BaseModel):
    is_completed: Optional[bool] = None
    completed_at: Optional[datetime] = None
