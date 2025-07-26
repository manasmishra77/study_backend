from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from datetime import datetime, timedelta
from typing import List
from app.models.user import UserResponse, UserUpdate, UserStats
from app.utils.auth import get_current_user
from app.utils.database import get_database, get_object_id, serialize_object_id
from app.utils.cloudinary_utils import upload_image_to_cloudinary, delete_image_from_cloudinary

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update user profile."""
    db = get_database()
    
    # Prepare update data
    update_data = {}
    if user_update.first_name is not None:
        update_data["first_name"] = user_update.first_name
    if user_update.last_name is not None:
        update_data["last_name"] = user_update.last_name
    
    if not update_data:
        return current_user
    
    update_data["updated_at"] = datetime.utcnow()
    
    # Update user in database
    await db.users.update_one(
        {"_id": get_object_id(current_user["id"])},
        {"$set": update_data}
    )
    
    # Return updated user
    updated_user = await db.users.find_one({"_id": get_object_id(current_user["id"])})
    return serialize_object_id(updated_user)

@router.post("/profile/picture")
async def update_profile_picture(
    file: UploadFile = File(...), 
    current_user: dict = Depends(get_current_user)
):
    """Upload and update user profile picture."""
    db = get_database()
    
    try:
        # Delete old profile picture if exists
        if current_user.get("profile_picture_url"):
            # Extract public_id from current URL if it's a Cloudinary URL
            # This is a simplified approach - you might want to store public_id separately
            pass
        
        # Upload new image
        upload_result = await upload_image_to_cloudinary(file, folder="profile_pictures")
        
        # Update user record
        await db.users.update_one(
            {"_id": get_object_id(current_user["id"])},
            {
                "$set": {
                    "profile_picture_url": upload_result["url"],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "message": "Profile picture updated successfully",
            "profile_picture_url": upload_result["url"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile picture: {str(e)}"
        )

@router.get("/learning-stats", response_model=UserStats)
async def get_learning_stats(current_user: dict = Depends(get_current_user)):
    """Get user learning statistics."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    # Get total notes
    total_notes = await db.notes.count_documents({"user_id": user_id})
    
    # Get total questions
    total_questions = await db.questions.count_documents({"user_id": user_id})
    
    # Get subjects studied
    subjects_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$subject"}},
        {"$count": "subjects_count"}
    ]
    subjects_result = await db.notes.aggregate(subjects_pipeline).to_list(1)
    subjects_studied = subjects_result[0]["subjects_count"] if subjects_result else 0
    
    # Get questions this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    questions_this_week = await db.questions.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": week_ago}
    })
    
    # Get weak and strong areas from analytics
    analytics = await db.learning_analytics.find_one({"user_id": user_id})
    weak_areas = analytics.get("weak_areas", []) if analytics else []
    strong_areas = analytics.get("strong_areas", []) if analytics else []
    
    return UserStats(
        total_notes=total_notes,
        total_questions=total_questions,
        subjects_studied=subjects_studied,
        questions_this_week=questions_this_week,
        weak_areas=weak_areas,
        strong_areas=strong_areas
    )

@router.delete("/account")
async def delete_user_account(current_user: dict = Depends(get_current_user)):
    """Delete user account and all associated data."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    try:
        # Delete user's images from Cloudinary
        notes = await db.notes.find({"user_id": user_id}).to_list(None)
        for note in notes:
            if note.get("cloudinary_public_id"):
                await delete_image_from_cloudinary(note["cloudinary_public_id"])
        
        # Delete all user data
        await db.users.delete_one({"_id": user_id})
        await db.notes.delete_many({"user_id": user_id})
        await db.questions.delete_many({"user_id": user_id})
        await db.suggested_questions.delete_many({"user_id": user_id})
        await db.learning_analytics.delete_many({"user_id": user_id})
        
        # Delete feedback for user's questions
        user_questions = await db.questions.find({"user_id": user_id}).to_list(None)
        question_ids = [q["_id"] for q in user_questions]
        await db.feedback.delete_many({"question_id": {"$in": question_ids}})
        
        return {"message": "Account deleted successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )
