from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List

class LearningAnalytics(BaseModel):
    id: str
    user_id: str
    subject: str
    topic: str
    questions_asked: int
    questions_answered: int
    difficulty_distribution: Dict[str, int]
    weak_areas: List[str]
    strong_areas: List[str]
    last_activity: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AnalyticsOverview(BaseModel):
    total_notes: int
    total_questions: int
    subjects_count: int
    questions_this_week: int
    questions_this_month: int
    most_active_subject: str
    avg_questions_per_note: float
    difficulty_breakdown: Dict[str, int]

class WeakAreasResponse(BaseModel):
    subject: str
    weak_topics: List[str]
    questions_needed: int
    last_studied: datetime

class SubjectProgress(BaseModel):
    subject: str
    total_questions: int
    questions_by_difficulty: Dict[str, int]
    topics_covered: List[str]
    weak_topics: List[str]
    strong_topics: List[str]
    progress_percentage: float
    recent_activity: List[datetime]

class QuestionPattern(BaseModel):
    question_type: str
    frequency: int
    avg_difficulty: str
    subjects: List[str]
    success_rate: float

class WeakAreasUpdate(BaseModel):
    weak_areas: List[str]
