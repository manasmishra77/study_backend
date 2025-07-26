from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from typing import List
from app.models.analytics import (
    AnalyticsOverview, WeakAreasResponse, SubjectProgress, 
    QuestionPattern, WeakAreasUpdate
)
from app.utils.auth import get_current_user
from app.utils.database import get_database, get_object_id

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(current_user: dict = Depends(get_current_user)):
    """Get overall analytics overview for the user."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    # Get basic counts
    total_notes = await db.notes.count_documents({"user_id": user_id})
    total_questions = await db.questions.count_documents({"user_id": user_id})
    
    # Get subjects count
    subjects_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$subject"}},
        {"$count": "count"}
    ]
    subjects_result = await db.notes.aggregate(subjects_pipeline).to_list(1)
    subjects_count = subjects_result[0]["count"] if subjects_result else 0
    
    # Get questions this week and month
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)
    
    questions_this_week = await db.questions.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": week_ago}
    })
    
    questions_this_month = await db.questions.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": month_ago}
    })
    
    # Get most active subject
    most_active_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$subject", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    most_active_result = await db.questions.aggregate(most_active_pipeline).to_list(1)
    most_active_subject = most_active_result[0]["_id"] if most_active_result else "None"
    
    # Calculate average questions per note
    avg_questions_per_note = total_questions / total_notes if total_notes > 0 else 0
    
    # Get difficulty breakdown
    difficulty_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$difficulty_level", "count": {"$sum": 1}}}
    ]
    difficulty_result = await db.questions.aggregate(difficulty_pipeline).to_list(None)
    difficulty_breakdown = {item["_id"]: item["count"] for item in difficulty_result}
    
    return AnalyticsOverview(
        total_notes=total_notes,
        total_questions=total_questions,
        subjects_count=subjects_count,
        questions_this_week=questions_this_week,
        questions_this_month=questions_this_month,
        most_active_subject=most_active_subject,
        avg_questions_per_note=avg_questions_per_note,
        difficulty_breakdown=difficulty_breakdown
    )

@router.get("/weak-areas", response_model=List[WeakAreasResponse])
async def get_weak_areas(current_user: dict = Depends(get_current_user)):
    """Get user's weak areas by subject."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    analytics = await db.learning_analytics.find({"user_id": user_id}).to_list(None)
    
    weak_areas = []
    for analytic in analytics:
        if analytic.get("weak_areas"):
            weak_areas.append(WeakAreasResponse(
                subject=analytic["subject"],
                weak_topics=analytic["weak_areas"],
                questions_needed=len(analytic["weak_areas"]) * 3,  # Suggest 3 questions per weak topic
                last_studied=analytic["last_activity"]
            ))
    
    return weak_areas

@router.get("/progress/{subject}", response_model=SubjectProgress)
async def get_subject_progress(subject: str, current_user: dict = Depends(get_current_user)):
    """Get detailed progress for a specific subject."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    # Get total questions for subject
    total_questions = await db.questions.count_documents({
        "user_id": user_id,
        "subject": subject
    })
    
    # Get questions by difficulty
    difficulty_pipeline = [
        {"$match": {"user_id": user_id, "subject": subject}},
        {"$group": {"_id": "$difficulty_level", "count": {"$sum": 1}}}
    ]
    difficulty_result = await db.questions.aggregate(difficulty_pipeline).to_list(None)
    questions_by_difficulty = {item["_id"]: item["count"] for item in difficulty_result}
    
    # Get topics covered
    topics_pipeline = [
        {"$match": {"user_id": user_id, "subject": subject}},
        {"$group": {"_id": "$topic"}},
        {"$match": {"_id": {"$ne": None}}}
    ]
    topics_result = await db.questions.aggregate(topics_pipeline).to_list(None)
    topics_covered = [item["_id"] for item in topics_result]
    
    # Get analytics for weak/strong areas
    analytics = await db.learning_analytics.find_one({
        "user_id": user_id,
        "subject": subject
    })
    
    weak_topics = analytics.get("weak_areas", []) if analytics else []
    strong_topics = analytics.get("strong_areas", []) if analytics else []
    
    # Calculate progress percentage (simplified)
    progress_percentage = min((total_questions / 10) * 100, 100) if total_questions > 0 else 0
    
    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_pipeline = [
        {"$match": {
            "user_id": user_id,
            "subject": subject,
            "created_at": {"$gte": thirty_days_ago}
        }},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}}},
        {"$sort": {"_id": 1}}
    ]
    recent_result = await db.questions.aggregate(recent_pipeline).to_list(None)
    recent_activity = [datetime.strptime(item["_id"], "%Y-%m-%d") for item in recent_result]
    
    return SubjectProgress(
        subject=subject,
        total_questions=total_questions,
        questions_by_difficulty=questions_by_difficulty,
        topics_covered=topics_covered,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        progress_percentage=progress_percentage,
        recent_activity=recent_activity
    )

@router.get("/question-patterns", response_model=List[QuestionPattern])
async def get_question_patterns(current_user: dict = Depends(get_current_user)):
    """Get question patterns and types for the user."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    # Get question type patterns
    patterns_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$question_type",
            "frequency": {"$sum": 1},
            "difficulties": {"$push": "$difficulty_level"},
            "subjects": {"$addToSet": "$subject"}
        }}
    ]
    
    patterns_result = await db.questions.aggregate(patterns_pipeline).to_list(None)
    
    patterns = []
    for pattern in patterns_result:
        # Calculate average difficulty (simplified)
        difficulties = pattern["difficulties"]
        easy_count = difficulties.count("easy")
        medium_count = difficulties.count("medium")
        hard_count = difficulties.count("hard")
        
        if hard_count > medium_count and hard_count > easy_count:
            avg_difficulty = "hard"
        elif medium_count > easy_count:
            avg_difficulty = "medium"
        else:
            avg_difficulty = "easy"
        
        patterns.append(QuestionPattern(
            question_type=pattern["_id"],
            frequency=pattern["frequency"],
            avg_difficulty=avg_difficulty,
            subjects=pattern["subjects"],
            success_rate=0.0  # Placeholder - would need feedback analysis
        ))
    
    return patterns

@router.post("/update-weak-areas")
async def update_weak_areas(
    weak_areas_update: WeakAreasUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update user's weak areas manually."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    # Update all analytics records for the user
    await db.learning_analytics.update_many(
        {"user_id": user_id},
        {
            "$set": {
                "weak_areas": weak_areas_update.weak_areas,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Weak areas updated successfully"}
