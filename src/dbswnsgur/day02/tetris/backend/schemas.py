from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


class TokenRefresh(BaseModel):
    refresh_token: str


class ScoreCreate(BaseModel):
    score: int
    level: int
    lines: int


class ScoreResponse(BaseModel):
    id: int
    score: int
    level: int
    lines: int
    created_at: datetime
    username: str
