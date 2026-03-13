from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, RefreshTokenRequest, UserUpdate
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "icon": "restaurant", "color": "#FF6B6B", "type": "expense"},
    {"name": "Transport", "icon": "directions_car", "color": "#4ECDC4", "type": "expense"},
    {"name": "Shopping", "icon": "shopping_bag", "color": "#45B7D1", "type": "expense"},
    {"name": "Entertainment", "icon": "movie", "color": "#96CEB4", "type": "expense"},
    {"name": "Health", "icon": "favorite", "color": "#FFEAA7", "type": "expense"},
    {"name": "Bills & Utilities", "icon": "receipt", "color": "#DDA0DD", "type": "expense"},
    {"name": "Education", "icon": "school", "color": "#98D8C8", "type": "expense"},
    {"name": "Other Expense", "icon": "category", "color": "#B0B0B0", "type": "expense"},
    {"name": "Salary", "icon": "work", "color": "#6C63FF", "type": "income"},
    {"name": "Freelance", "icon": "laptop", "color": "#FF9F43", "type": "income"},
    {"name": "Investment", "icon": "trending_up", "color": "#54A0FF", "type": "income"},
    {"name": "Other Income", "icon": "attach_money", "color": "#5F27CD", "type": "income"},
]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hash_password(user_data.password),
        currency=user_data.currency,
    )
    db.add(user)
    await db.flush()

    for cat in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user.id, **cat))

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if update_data.name:
        current_user.name = update_data.name
    if update_data.currency:
        current_user.currency = update_data.currency
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
