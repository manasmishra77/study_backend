from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from typing import List
from app.models.question import SuggestedQuestionResponse
from app.utils.auth import get_current_user
from app.utils.database import get_database, get_object_id, serialize_object_id

router = APIRouter(prefix="/api/suggestions", tags=["Suggested Questions"])

@router.get("/questions", response_model=List[SuggestedQuestionResponse])
async def get_suggested_questions(current_user: dict = Depends(get_current_user)):
    """Get suggested questions for the current user."""
    db = get_database()
    
    suggestions = await db.suggested_questions.find({
        "user_id": get_object_id(current_user["id"]),
        "is_completed": False
    }).sort("suggested_at", -1).to_list(None)
    
    return [serialize_object_id(suggestion) for suggestion in suggestions]

@router.post("/generate")
async def generate_suggestions(current_user: dict = Depends(get_current_user)):
    """Generate new suggested questions based on user's weak areas (placeholder for LLM integration)."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    # Get user's learning analytics to identify weak areas
    analytics = await db.learning_analytics.find({"user_id": user_id}).to_list(None)
    
    if not analytics:
        return {"message": "No learning data available for suggestions"}
    
    # TODO: Integrate with LLM to generate personalized questions
    # For now, create placeholder suggestions
    
    suggested_questions = []
    for analytic in analytics:
        if analytic.get("weak_areas"):
            for weak_area in analytic["weak_areas"][:3]:  # Limit to 3 per subject
                suggestion = {
                    "user_id": user_id,
                    "question_text": f"Review question about {weak_area} in {analytic['subject']}",
                    "subject": analytic["subject"],
                    "topic": weak_area,
                    "difficulty_level": "medium",
                    "based_on_weak_areas": [weak_area],
                    "is_completed": False,
                    "suggested_at": datetime.utcnow()
                }
                suggested_questions.append(suggestion)
    
    if suggested_questions:
        await db.suggested_questions.insert_many(suggested_questions)
        return {"message": f"Generated {len(suggested_questions)} new suggestions"}
    
    return {"message": "No new suggestions generated"}

@router.put("/{suggestion_id}/complete")
async def complete_suggestion(suggestion_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a suggested question as completed."""
    db = get_database()
    
    # Check if suggestion exists and belongs to user
    suggestion = await db.suggested_questions.find_one({
        "_id": get_object_id(suggestion_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    # Update suggestion as completed
    await db.suggested_questions.update_one(
        {"_id": get_object_id(suggestion_id)},
        {
            "$set": {
                "is_completed": True,
                "completed_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Suggestion marked as completed"}

@router.get("/history", response_model=List[SuggestedQuestionResponse])
async def get_suggestion_history(current_user: dict = Depends(get_current_user)):
    """Get completed suggestion history for the current user."""
    db = get_database()
    
    completed_suggestions = await db.suggested_questions.find({
        "user_id": get_object_id(current_user["id"]),
        "is_completed": True
    }).sort("completed_at", -1).to_list(None)
    
    return [serialize_object_id(suggestion) for suggestion in completed_suggestions]
