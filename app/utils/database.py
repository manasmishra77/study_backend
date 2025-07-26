import motor.motor_asyncio
from bson import ObjectId
from typing import Optional
from app.core.config import settings

# MongoDB client
client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
database = client[settings.database_name]

def get_database():
    """Get database instance."""
    return database

def get_object_id(id_str: str) -> ObjectId:
    """Convert string ID to ObjectId."""
    try:
        return ObjectId(id_str)
    except Exception:
        raise ValueError(f"Invalid ObjectId: {id_str}")

def serialize_object_id(obj: dict) -> dict:
    """Convert ObjectId to string in dictionary."""
    if obj is None:
        return None
    
    if "_id" in obj:
        obj["id"] = str(obj["_id"])
        del obj["_id"]
    
    # Handle nested ObjectIds
    for key, value in obj.items():
        if isinstance(value, ObjectId):
            obj[key] = str(value)
        elif isinstance(value, list):
            obj[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
    
    return obj

async def create_indexes():
    """Create database indexes for better performance."""
    # Users collection
    await database.users.create_index("email", unique=True)
    
    # Notes collection
    await database.notes.create_index("user_id")
    await database.notes.create_index("subject")
    await database.notes.create_index([("user_id", 1), ("subject", 1)])
    
    # Questions collection
    await database.questions.create_index("user_id")
    await database.questions.create_index("note_id")
    await database.questions.create_index([("user_id", 1), ("subject", 1)])
    
    # Feedback collection
    await database.feedback.create_index("question_id")
    
    # Suggested questions collection
    await database.suggested_questions.create_index("user_id")
    await database.suggested_questions.create_index([("user_id", 1), ("is_completed", 1)])
    
    # Learning analytics collection
    await database.learning_analytics.create_index("user_id")
    await database.learning_analytics.create_index([("user_id", 1), ("subject", 1)])
