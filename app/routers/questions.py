from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from typing import List
from app.models.question import (
    QuestionCreate, QuestionResponse, QuestionUpdate, 
    FeedbackCreate, FeedbackResponse, QuestionWithFeedback
)
from app.utils.auth import get_current_user
from app.utils.database import get_database, get_object_id, serialize_object_id

router = APIRouter(prefix="/api/questions", tags=["Questions"])

@router.post("", response_model=QuestionResponse)
async def create_question(
    question: QuestionCreate, 
    current_user: dict = Depends(get_current_user)
):
    """Create a new question related to a note."""
    db = get_database()
    
    # Verify note exists and belongs to user
    note = await db.notes.find_one({
        "_id": get_object_id(question.note_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    # Create question document
    question_data = {
        "user_id": get_object_id(current_user["id"]),
        "note_id": get_object_id(question.note_id),
        "question_text": question.question_text,
        "subject": question.subject,
        "topic": question.topic,
        "difficulty_level": question.difficulty_level,
        "question_type": question.question_type,
        "created_at": datetime.utcnow()
    }
    
    result = await db.questions.insert_one(question_data)
    question_data["_id"] = result.inserted_id
    
    # Update learning analytics
    await update_learning_analytics(db, current_user["id"], question.subject, question.topic)
    
    return serialize_object_id(question_data)

@router.get("", response_model=List[QuestionResponse])
async def get_user_questions(current_user: dict = Depends(get_current_user)):
    """Get all questions for the current user."""
    db = get_database()
    
    questions = await db.questions.find(
        {"user_id": get_object_id(current_user["id"])}
    ).sort("created_at", -1).to_list(None)
    
    return [serialize_object_id(question) for question in questions]

@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question_by_id(question_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific question by ID."""
    db = get_database()
    
    question = await db.questions.find_one({
        "_id": get_object_id(question_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    return serialize_object_id(question)

@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str, 
    question_update: QuestionUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update a question."""
    db = get_database()
    
    # Check if question exists and belongs to user
    question = await db.questions.find_one({
        "_id": get_object_id(question_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Prepare update data
    update_data = {}
    if question_update.question_text is not None:
        update_data["question_text"] = question_update.question_text
    if question_update.subject is not None:
        update_data["subject"] = question_update.subject
    if question_update.topic is not None:
        update_data["topic"] = question_update.topic
    if question_update.difficulty_level is not None:
        update_data["difficulty_level"] = question_update.difficulty_level
    if question_update.question_type is not None:
        update_data["question_type"] = question_update.question_type
    
    if not update_data:
        return serialize_object_id(question)
    
    # Update question
    await db.questions.update_one(
        {"_id": get_object_id(question_id)},
        {"$set": update_data}
    )
    
    # Return updated question
    updated_question = await db.questions.find_one({"_id": get_object_id(question_id)})
    return serialize_object_id(updated_question)

@router.delete("/{question_id}")
async def delete_question(question_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a question and its feedback."""
    db = get_database()
    
    # Check if question exists and belongs to user
    question = await db.questions.find_one({
        "_id": get_object_id(question_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Delete question and associated feedback
    question_obj_id = get_object_id(question_id)
    await db.questions.delete_one({"_id": question_obj_id})
    await db.feedback.delete_many({"question_id": question_obj_id})
    
    return {"message": "Question deleted successfully"}

@router.get("/by-note/{note_id}", response_model=List[QuestionResponse])
async def get_questions_by_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """Get all questions for a specific note."""
    db = get_database()
    
    # Verify note belongs to user
    note = await db.notes.find_one({
        "_id": get_object_id(note_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    questions = await db.questions.find({
        "note_id": get_object_id(note_id)
    }).sort("created_at", -1).to_list(None)
    
    return [serialize_object_id(question) for question in questions]

@router.post("/{question_id}/feedback", response_model=FeedbackResponse)
async def add_feedback(
    question_id: str, 
    feedback: FeedbackCreate, 
    current_user: dict = Depends(get_current_user)
):
    """Add feedback to a question."""
    db = get_database()
    
    # Verify question exists and belongs to user
    question = await db.questions.find_one({
        "_id": get_object_id(question_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Create feedback document
    feedback_data = {
        "question_id": get_object_id(question_id),
        "feedback_text": feedback.feedback_text,
        "feedback_type": feedback.feedback_type,
        "is_ai_generated": False,  # Manual feedback for now
        "created_at": datetime.utcnow()
    }
    
    result = await db.feedback.insert_one(feedback_data)
    feedback_data["_id"] = result.inserted_id
    
    return serialize_object_id(feedback_data)

@router.get("/{question_id}/feedback", response_model=List[FeedbackResponse])
async def get_question_feedback(question_id: str, current_user: dict = Depends(get_current_user)):
    """Get all feedback for a question."""
    db = get_database()
    
    # Verify question exists and belongs to user
    question = await db.questions.find_one({
        "_id": get_object_id(question_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    feedback_list = await db.feedback.find({
        "question_id": get_object_id(question_id)
    }).sort("created_at", -1).to_list(None)
    
    return [serialize_object_id(feedback) for feedback in feedback_list]

async def update_learning_analytics(db, user_id: str, subject: str, topic: str):
    """Update learning analytics when a question is created."""
    user_obj_id = get_object_id(user_id)
    
    # Find or create analytics record
    analytics = await db.learning_analytics.find_one({
        "user_id": user_obj_id,
        "subject": subject
    })
    
    if analytics:
        # Update existing record
        await db.learning_analytics.update_one(
            {"_id": analytics["_id"]},
            {
                "$inc": {"questions_asked": 1},
                "$set": {
                    "last_activity": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                "$addToSet": {"topic": topic} if topic else {}
            }
        )
    else:
        # Create new analytics record
        analytics_data = {
            "user_id": user_obj_id,
            "subject": subject,
            "topic": topic or "",
            "questions_asked": 1,
            "questions_answered": 0,
            "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
            "weak_areas": [],
            "strong_areas": [],
            "last_activity": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.learning_analytics.insert_one(analytics_data)
