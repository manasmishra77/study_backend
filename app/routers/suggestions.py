from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from datetime import datetime
from typing import List, Optional
import uuid
import tempfile
import os
import pdb

from app.models.question import SuggestedQuestionResponse
from app.models.suggestion import AssignmentEvaluationResponse, Hint, EvaluationResult, SuggestedQuestion
from app.utils.auth import get_current_user
from app.utils.database import get_database, get_object_id, serialize_object_id
from app.utils.cloudinary_utils import upload_image_to_cloudinary
from app.study_agent.rag_utils import RAGManager
from app.core.config import settings
from app.study_agent.main import EducationalTutorSystem

router = APIRouter(prefix="/api/suggestions", tags=["Suggested Questions"])

@router.post("/evaluate-assignment", response_model=AssignmentEvaluationResponse)
async def evaluate_assignment(
    image: UploadFile = File(...),
    subject: str = Form(...),
    chapter: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Evaluate student's handwritten assignment and provide suggestions.
    
    This endpoint:
    1. Analyzes the handwritten assignment image
    2. Evaluates solved questions
    3. Provides hints for unsolved questions
    4. Suggests questions for weak areas
    5. Suggests advanced questions for further learning
    """
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    # Validate image file
    if not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    try:
        # Read image content
        image_content = await image.read()
        
        # Upload image to Cloudinary
        await image.seek(0)  # Reset file position
        upload_result = await upload_image_to_cloudinary(image, folder="assignments")

        # Create temporary file for image processing
        temp_image_path = None
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_image_path = temp_file.name
            temp_file.write(image_content)

        # Now you can use temp_image_path with your EducationalTutorSystem
        system = EducationalTutorSystem(
            api_key=settings.google_api_key, 
            board=current_user.get("board", "CBSE"),
            class_name=current_user.get("class_name", "Class 10"), 
            subject=subject
        )
        pdb.set_trace()
        # Use the temporary file path for processing
        result = system.process_math_problem(temp_image_path, "Solve this for me")
        
        # Mock evaluation - replace with actual AI analysis
        evaluation_results = [
            EvaluationResult(
                question_number="Q1",
                is_correct=False,
                score=0.3,
                errors_found=[
                    "Calculation error in step 3",
                    "Wrong formula applied for area calculation"
                ],
                correct_approach="Use formula: Area = π × r²",
                student_approach="Used formula: Area = 2πr",
                feedback="You confused circumference formula with area formula. Remember: Area uses r², circumference uses 2r."
            ),
            EvaluationResult(
                question_number="Q2",
                is_correct=True,
                score=1.0,
                errors_found=[],
                correct_approach="Correctly applied quadratic formula",
                student_approach="Used quadratic formula: (-b ± √(b²-4ac))/2a",
                feedback="Excellent work! Your solution is completely correct."
            )
        ]
        
        # Mock hints for unsolved questions
        hints = [
            Hint(
                question_number="Q3",
                question_text="Find the value of x in the equation: 2x + 5 = 13",
                hint_text="Start by isolating the term with x. Subtract 5 from both sides first.",
                difficulty_level="easy",
                next_steps=[
                    "Subtract 5 from both sides: 2x = 8",
                    "Divide both sides by 2: x = 4",
                    "Verify by substituting back into original equation"
                ]
            )
        ]
        
        # Mock suggested questions for weak areas
        weak_area_questions = [
            SuggestedQuestion(
                question_text="Calculate the area of a circle with radius 7 cm.",
                difficulty_level="medium",
                topic="Circle Area",
                reason="Practice needed in area calculations based on your Q1 performance",
                question_type="weak_area"
            ),
            SuggestedQuestion(
                question_text="Find the area of a semicircle with diameter 14 cm.",
                difficulty_level="medium",
                topic="Circle Area",
                reason="Building on circle area concepts",
                question_type="weak_area"
            )
        ]
        
        # Mock advanced questions
        advanced_questions = [
            SuggestedQuestion(
                question_text="Solve the system of equations: 2x + 3y = 12 and x - y = 1",
                difficulty_level="hard",
                topic="Systems of Equations",
                reason="Next level challenge based on your strong algebra skills",
                question_type="advanced"
            )
        ]
        
        # Calculate summary statistics
        total_questions = len(evaluation_results) + len(hints)
        questions_correct = sum(1 for result in evaluation_results if result.is_correct)
        questions_incorrect = sum(1 for result in evaluation_results if not result.is_correct)
        questions_unsolved = len(hints)
        overall_score = sum(result.score for result in evaluation_results) / len(evaluation_results) if evaluation_results else 0.0
        
        # Store evaluation in database
        evaluation_data = {
            "user_id": user_id,
            "subject": subject,
            "chapter": chapter,
            "processed_at": datetime.utcnow(),
            "image_url": upload_result["url"],
            "cloudinary_public_id": upload_result["public_id"],
            "processing_status": "completed",
            "overall_score": overall_score,
            "total_questions_evaluated": total_questions,
            "questions_correct": questions_correct,
            "questions_incorrect": questions_incorrect,
            "questions_unsolved": questions_unsolved,
            "evaluation_results": [result.dict() for result in evaluation_results],
            "hints": [hint.dict() for hint in hints],
            "weak_area_questions": [q.dict() for q in weak_area_questions],
            "advanced_questions": [q.dict() for q in advanced_questions]
        }
        
        result = await db.assignment_evaluations.insert_one(evaluation_data)
        evaluation_data["_id"] = result.inserted_id
        
        # Return the complete evaluation response
        return AssignmentEvaluationResponse(
            id=str(result.inserted_id),
            user_id=str(user_id),
            subject=subject,
            chapter=chapter,
            processed_at=evaluation_data["processed_at"],
            hints=hints,
            evaluation_results=evaluation_results,
            weak_area_questions=weak_area_questions,
            advanced_questions=advanced_questions,
            overall_score=overall_score,
            total_questions_evaluated=total_questions,
            questions_correct=questions_correct,
            questions_incorrect=questions_incorrect,
            questions_unsolved=questions_unsolved,
            image_url=upload_result["url"],
            cloudinary_public_id=upload_result["public_id"],
            processing_status="completed"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate assignment: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
            except Exception as e:
                print(f"Warning: Could not delete temp file {temp_image_path}: {e}")

@router.get("/evaluations", response_model=List[AssignmentEvaluationResponse])
async def get_assignment_evaluations(current_user: dict = Depends(get_current_user)):
    """Get all assignment evaluations for the current user."""
    db = get_database()
    user_id = get_object_id(current_user["id"])
    
    evaluations = await db.assignment_evaluations.find({
        "user_id": user_id
    }).sort("processed_at", -1).to_list(None)
    
    return [serialize_object_id(evaluation) for evaluation in evaluations]

@router.get("/evaluations/{evaluation_id}", response_model=AssignmentEvaluationResponse)
async def get_assignment_evaluation(
    evaluation_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Get a specific assignment evaluation."""
    db = get_database()
    
    evaluation = await db.assignment_evaluations.find_one({
        "_id": get_object_id(evaluation_id),
        "user_id": get_object_id(current_user["id"])
    })
    
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment evaluation not found"
        )
    
    return serialize_object_id(evaluation)
