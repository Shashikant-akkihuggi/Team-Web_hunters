from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import get_db
from backend.app.models import User, UserRole, AuditLog
from backend.app.schemas import UserResponse, UserUpdate, UserChangePassword
from backend.app.auth import get_current_user, verify_password, get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """View current user's profile and account information."""
    return UserResponse.model_validate(current_user)

@router.patch("/me", response_model=UserResponse)
def update_current_user_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user profile (full name)."""
    if user_update.full_name is not None:
        trimmed = user_update.full_name.strip()
        if len(trimmed) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Full name must be at least 2 characters long."
            )
        current_user.full_name = trimmed

    db.commit()
    db.refresh(current_user)

    audit = AuditLog(
        user_id=current_user.id,
        action="USER_PROFILE_UPDATED",
        entity_type="USER",
        entity_id=current_user.id,
        details={"full_name": current_user.full_name}
    )
    db.add(audit)
    db.commit()

    return UserResponse.model_validate(current_user)

@router.post("/change-password")
def change_password(
    pwd_data: UserChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change current user's password securely."""
    if not verify_password(pwd_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    if pwd_data.new_password != pwd_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match."
        )

    if len(pwd_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )

    current_user.hashed_password = get_password_hash(pwd_data.new_password)
    db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action="PASSWORD_CHANGED",
        entity_type="USER",
        entity_id=current_user.id,
        details={"email": current_user.email}
    )
    db.add(audit)
    db.commit()

    return {"message": "Password updated successfully."}

@router.get("/search", response_model=List[UserResponse])
def search_users(
    q: Optional[str] = Query(None, description="Search query for email or name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search registered users by email or name for team membership additions."""
    query = db.query(User).filter(User.is_active == True)
    if isinstance(q, str) and q.strip():
        search_fmt = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.email.ilike(search_fmt),
                User.full_name.ilike(search_fmt)
            )
        )
    users = query.limit(20).all()
    return [UserResponse.model_validate(u) for u in users]

@router.get("", response_model=List[UserResponse])
def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all active users."""
    query = db.query(User).filter(User.is_active == True)
    if isinstance(role, str) and role:
        query = query.filter(User.role == role.upper())
    if isinstance(search, str) and search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_fmt),
                User.email.ilike(search_fmt)
            )
        )
    users = query.all()
    return [UserResponse.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserResponse)
def get_user_profile(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user profile by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)
