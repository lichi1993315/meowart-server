"""User schemas for request/response validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr


class UserCreate(UserBase):
    """Schema for user registration with email/password."""

    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(UserBase):
    """Schema for user login with email/password."""

    password: str


class UserResponse(UserBase):
    """Schema for user response (public data)."""

    id: int
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Schema for user profile returned by /me endpoint."""

    id: int
    email: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Schema for authentication response."""

    message: str
    user: Optional[UserProfile] = None


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str
