from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any
from app.models.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from app.core.repository import users_repo
from app.core.security import hash_password, verify_password, create_access_token, get_current_user_token
from app.core.rate_limiter import check_rate_limit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserRegister, request: Request):
    check_rate_limit(request, endpoint_tag="auth_register")
    email_clean = payload.email.lower().strip()
    existing_user = await users_repo.find_one({"email": email_clean})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered."
        )

    hashed_pw = hash_password(payload.password)
    user_record = {
        "email": email_clean,
        "full_name": payload.full_name.strip(),
        "password_hash": hashed_pw
    }
    created_user = await users_repo.insert(user_record)
    user_id = created_user["id"]

    token = create_access_token({"sub": user_id, "email": email_clean})
    user_resp = UserResponse(
        id=user_id,
        email=email_clean,
        full_name=created_user["full_name"],
        created_at=created_user["created_at"]
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

@router.post("/login", response_model=TokenResponse)
async def login_user(payload: UserLogin, request: Request):
    check_rate_limit(request, endpoint_tag="auth_login")
    email_clean = payload.email.lower().strip()
    user = await users_repo.find_one({"email": email_clean})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    user_id = user["id"]
    token = create_access_token({"sub": user_id, "email": email_clean})
    user_resp = UserResponse(
        id=user_id,
        email=email_clean,
        full_name=user.get("full_name", "User"),
        created_at=user.get("created_at", "")
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(token_data: Dict[str, Any] = Depends(get_current_user_token)):
    user_id = token_data.get("sub")
    user = await users_repo.find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name", ""),
        created_at=user.get("created_at", "")
    )
