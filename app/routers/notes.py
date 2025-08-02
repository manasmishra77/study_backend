from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from datetime import datetime
from typing import List
from app.models.note import NoteResponse, NoteUpdate, NoteWithQuestions, SubjectStats
from app.utils.auth import get_current_user
from app.utils.database import get_database, get_object_id, serialize_object_id
from app.utils.cloudinary_utils import upload_image_to_cloudinary, delete_image_from_cloudinary
import pdb

router = APIRouter(prefix="/api/notes", tags=["Notes"])

@router.post("/upload", response_model=NoteResponse)
async def upload_note(
    file: UploadFile = File(...),
    title: str = Form(...),
    subject: str = Form(...),
    topic: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload a new handwritten note."""
    db = get_database()
    
    try:
        pdb.set_trace()
        # Upload image to Cloudinary
        upload_result = await upload_image_to_cloudinary(file, folder="notes")
        
        # Create note document
        note_data = {
            "user_id": get_object_id(current_user["id"]),
            "title": title,
            "subject": subject,
            "topic": topic,
            "image_url": upload_result["url"],
            "cloudinary_public_id": upload_result["public_id"],
            "extracted_text": None,  # For future OCR implementation
            "upload_date": datetime.utcnow(),
            "file_size": upload_result["bytes"],
            "file_type": file.content_type,
            "metadata": {
                "width": upload_result["width"],
                "height": upload_result["height"],
                "format": upload_result["format"]
            }
        }
        
        result = await db.notes.insert_one(note_data)
        note_data["_id"] = result.inserted_id
        
        return serialize_object_id(note_data)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload note: {str(e)}"
        )

@router.get("", response_model=List[NoteResponse])
async def get_user_notes(current_user: dict = Depends(get_current_user)):
    """Get all notes for the current user."""
    db = get_database()
    
    notes = await db.notes.find(
        {"user_id": get_object_id(current_user["id"])}
    ).sort("upload_date", -1).to_list(None)
    
    return [serialize_object_id(note) for note in notes]

@router.get("/{note_id}", response_model=NoteResponse)
async def get_note_by_id(note_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific note by ID."""
    db = get_database()
    
    note = await db.notes.find_one({
        "_id": get_object_id(note_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    return serialize_object_id(note)

@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str, 
    note_update: NoteUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update a note's metadata."""
    db = get_database()
    
    # Check if note exists and belongs to user
    note = await db.notes.find_one({
        "_id": get_object_id(note_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    # Prepare update data
    update_data = {}
    if note_update.title is not None:
        update_data["title"] = note_update.title
    if note_update.subject is not None:
        update_data["subject"] = note_update.subject
    if note_update.topic is not None:
        update_data["topic"] = note_update.topic
    
    if not update_data:
        return serialize_object_id(note)
    
    # Update note
    await db.notes.update_one(
        {"_id": get_object_id(note_id)},
        {"$set": update_data}
    )
    
    # Return updated note
    updated_note = await db.notes.find_one({"_id": get_object_id(note_id)})
    return serialize_object_id(updated_note)

@router.delete("/{note_id}")
async def delete_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a note and its associated data."""
    db = get_database()
    
    # Check if note exists and belongs to user
    note = await db.notes.find_one({
        "_id": get_object_id(note_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    try:
        # Delete image from Cloudinary
        if note.get("cloudinary_public_id"):
            await delete_image_from_cloudinary(note["cloudinary_public_id"])
        
        # Delete note and associated questions/feedback
        note_obj_id = get_object_id(note_id)
        await db.notes.delete_one({"_id": note_obj_id})
        
        # Delete associated questions
        questions = await db.questions.find({"note_id": note_obj_id}).to_list(None)
        question_ids = [q["_id"] for q in questions]
        
        await db.questions.delete_many({"note_id": note_obj_id})
        await db.feedback.delete_many({"question_id": {"$in": question_ids}})
        
        return {"message": "Note deleted successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete note: {str(e)}"
        )

@router.get("/subjects", response_model=List[str])
async def get_user_subjects(current_user: dict = Depends(get_current_user)):
    """Get all subjects for the current user."""
    db = get_database()
    
    pipeline = [
        {"$match": {"user_id": get_object_id(current_user["id"])}},
        {"$group": {"_id": "$subject"}},
        {"$sort": {"_id": 1}}
    ]
    
    subjects = await db.notes.aggregate(pipeline).to_list(None)
    return [subject["_id"] for subject in subjects]

@router.get("/by-subject/{subject}", response_model=List[NoteResponse])
async def get_notes_by_subject(subject: str, current_user: dict = Depends(get_current_user)):
    """Get all notes for a specific subject."""
    db = get_database()
    
    notes = await db.notes.find({
        "user_id": get_object_id(current_user["id"]),
        "subject": subject
    }).sort("upload_date", -1).to_list(None)
    
    return [serialize_object_id(note) for note in notes]
