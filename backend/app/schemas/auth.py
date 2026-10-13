"""Pydantic v2 schemas for User authentication and JWT tokens."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload to register a new user account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="User email address (stored lowercase).")
    display_name: str = Field(..., min_length=1, max_length=255, description="Full name or display name.")
    password: str = Field(..., min_length=10, max_length=128, description="Password (minimum 10 characters).")


class UserLoginRequest(BaseModel):
    """Payload for user authentication."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., min_length=1, description="Account password.")


class UserResponse(BaseModel):
    """Public user representation (never exposes password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
