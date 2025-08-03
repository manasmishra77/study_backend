from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class EvaluationResult(BaseModel):
    """Result of evaluating a solved question"""
    question_number: str
    is_correct: bool
    score: float  # 0.0 to 1.0
    errors_found: List[str]
    correct_approach: str
    student_approach: str
    feedback: str

class Hint(BaseModel):
    """Hint for unsolved questions"""
    question_number: str
    question_text: str
    hint_text: str
    difficulty_level: str
    next_steps: List[str]

class SuggestedQuestion(BaseModel):
    """Suggested question for practice"""
    question_text: str
    difficulty_level: str
    topic: str
    reason: str  # Why this question is suggested
    question_type: str  # "weak_area" or "advanced"

class AssignmentEvaluationResponse(BaseModel):
    """Complete response for assignment evaluation"""
    id: str
    user_id: str
    subject: str
    chapter: Optional[str] = None
    processed_at: datetime
    
    # Main response components
    hints: List[Hint]
    evaluation_results: List[EvaluationResult]
    weak_area_questions: List[SuggestedQuestion]
    advanced_questions: List[SuggestedQuestion]
    
    # Summary
    overall_score: float
    total_questions_evaluated: int
    questions_correct: int
    questions_incorrect: int
    questions_unsolved: int
    
    # Metadata
    image_url: str
    cloudinary_public_id: str
    processing_status: str
    
    class Config:
        from_attributes = True