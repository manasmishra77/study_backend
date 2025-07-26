from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from app.models.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse, 
    TokenRefresh, PasswordReset, PasswordResetConfirm
)
from app.core.security import (
    get_password_hash, verify_password, 
    create_access_token, create_refresh_token, verify_token
)
from app.utils.database import get_database, serialize_object_id
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    """Register a new user."""
    db = get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = get_password_hash(user.password)
    user_data = {
        "email": user.email,
        "password_hash": hashed_password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_picture_url": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    
    return serialize_object_id(user_data)

@router.post("/login", response_model=TokenResponse)
async def login_user(user: UserLogin):
    """Login user and return JWT tokens."""
    db = get_database()
    
    # Find user by email
    db_user = await db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(db_user["_id"])})
    refresh_token = create_refresh_token(data={"sub": str(db_user["_id"])})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh):
    """Refresh access token using refresh token."""
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Create new tokens
    access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout_user(current_user: dict = Depends(get_current_user)):
    """Logout user (placeholder for token blacklisting)."""
    # In a production app, you would blacklist the token here
    return {"message": "Successfully logged out"}

@router.post("/forgot-password")
async def forgot_password(password_reset: PasswordReset):
    """Send password reset email (placeholder)."""
    db = get_database()
    
    # Check if user exists
    user = await db.users.find_one({"email": password_reset.email})
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a reset link has been sent"}
    
    # TODO: Implement email sending logic here
    # For now, just return success message
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirm):
    """Reset password using reset token (placeholder)."""
    # TODO: Implement token verification and password reset logic
    # For now, just return success message
    return {"message": "Password has been reset successfully"}
