"""Authentication routes for Google OAuth and Email/Password login."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.oauth import oauth
from app.core.security import hash_password, verify_password
from app.db import get_db
from app.models import User
from app.schemas import AuthResponse, ErrorResponse, UserCreate, UserLogin, UserProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def set_session_cookie(response: Response, user_id: int) -> None:
    """Set session cookie with proper domain configuration for cross-subdomain support."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=str(user_id),
        domain=settings.SESSION_COOKIE_DOMAIN,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=settings.SESSION_COOKIE_SECURE,
        max_age=settings.SESSION_MAX_AGE,
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie by setting expiry to past."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        domain=settings.SESSION_COOKIE_DOMAIN,
    )


async def get_current_user_id(request: Request) -> Optional[int]:
    """Extract user ID from session cookie."""
    session_value = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_value:
        try:
            return int(session_value)
        except ValueError:
            return None
    return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user from session cookie."""
    user_id = await get_current_user_id(request)
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ============================================================================
# US-002: Google OAuth Login
# ============================================================================


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect user to Google's consent screen for OAuth login.

    GET /api/auth/google/login
    """
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle the return from Google OAuth.

    GET /api/auth/google/callback

    Logic (Auto-Merge):
    - If Google email does NOT exist in DB -> Create new user -> Set Session
    - If Google email EXISTS in DB -> Update user record with google_id -> Set Session
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate with Google",
        )

    # Get user info from Google
    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Google",
        )

    email = user_info.get("email")
    google_id = user_info.get("sub")
    avatar_url = user_info.get("picture")

    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user info from Google",
        )

    # Check if user exists by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # User exists - merge by updating google_id if not already set
        if user.google_id is None:
            user.google_id = google_id
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
        user = User(
            email=email,
            google_id=google_id,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Create redirect response to frontend
    from starlette.responses import RedirectResponse

    response = RedirectResponse(url=settings.FRONTEND_URL, status_code=status.HTTP_302_FOUND)
    set_session_cookie(response, user.id)

    return response


# ============================================================================
# US-003: Email Registration
# ============================================================================


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def register(
    user_data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email and password.

    POST /api/auth/register
    Body: {email, password}

    - Validates email format (via Pydantic)
    - Checks if email already exists -> returns 400 error
    - Hashes password before storing
    - Automatically logs user in (sets session) upon success
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user with hashed password
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Set session cookie to log user in
    set_session_cookie(response, user.id)

    return AuthResponse(
        message="Registration successful",
        user=UserProfile(id=user.id, email=user.email, avatar_url=user.avatar_url),
    )


# ============================================================================
# US-004: Email Login
# ============================================================================


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password.

    POST /api/auth/login
    Body: {email, password}

    - Finds user by email -> verifies password hash
    - If valid -> Sets session cookie
    - If invalid -> Returns 401 error
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Set session cookie
    set_session_cookie(response, user.id)

    return AuthResponse(
        message="Login successful",
        user=UserProfile(id=user.id, email=user.email, avatar_url=user.avatar_url),
    )


# ============================================================================
# US-005: "Who Am I" (Session Check)
# ============================================================================


@router.get(
    "/me",
    response_model=UserProfile,
    responses={401: {"model": ErrorResponse}},
)
async def get_me(
    user: Optional[User] = Depends(get_current_user),
):
    """Get current user profile from session.

    GET /api/auth/me

    - If cookie is valid -> Return user profile (id, email, avatar)
    - If cookie is missing/invalid -> Return 401 Unauthorized
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return UserProfile(id=user.id, email=user.email, avatar_url=user.avatar_url)


# ============================================================================
# US-006: Logout
# ============================================================================


@router.post("/logout", response_model=AuthResponse)
async def logout(response: Response):
    """Logout and clear session cookie.

    POST /api/auth/logout

    - Clears the session cookie (sets expiry to past)
    - Returns success message
    """
    clear_session_cookie(response)
    return AuthResponse(message="Logged out successfully")
