import re
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, UserRole, AuditLog
from backend.app.schemas import UserCreate, UserRegister, UserLogin, UserResponse, Token
from backend.app.auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: Union[UserRegister, UserCreate], db: Session = Depends(get_db)):
    # 1. Validate email format
    if not re.match(EMAIL_REGEX, user_in.email.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format. Please provide a valid email address."
        )

    # 2. Check confirm password if provided
    if hasattr(user_in, 'confirm_password') and user_in.confirm_password is not None:
        if user_in.password != user_in.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password and confirmation password do not match."
            )

    # 3. Check password length
    if len(user_in.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    # 4. Check for duplicate email
    normalized_email = user_in.email.strip().lower()
    existing_user = db.query(User).filter(User.email.ilike(normalized_email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists. Please login or use a different email."
        )

    # 5. Create user
    user = User(
        email=normalized_email,
        full_name=user_in.full_name.strip(),
        hashed_password=get_password_hash(user_in.password),
        role=getattr(user_in, 'role', None) or UserRole.INCOMING_MEMBER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 6. Audit log
    audit = AuditLog(
        user_id=user.id,
        action="USER_REGISTERED",
        entity_type="USER",
        entity_id=user.id,
        details={"email": user.email, "full_name": user.full_name, "role": user.role}
    )
    db.add(audit)
    db.commit()

    # 7. Generate JWT token
    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    normalized_email = credentials.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(normalized_email)).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated. Please contact an administrator."
        )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=user.id,
        details={"email": user.email}
    )
    db.add(audit)
    db.commit()

    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit = AuditLog(
        user_id=current_user.id,
        action="USER_LOGOUT",
        entity_type="USER",
        entity_id=current_user.id,
        details={"email": current_user.email}
    )
    db.add(audit)
    db.commit()
    return {"message": "Successfully logged out. Please discard your authentication token."}
