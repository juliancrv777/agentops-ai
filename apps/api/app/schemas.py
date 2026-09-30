from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str | None = Field(default=None, max_length=160)
    organization_name: str = Field(min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    display_name: str | None
    organization_id: UUID
    role: str


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    mime_type: str | None
    size_bytes: int | None
    status: str
    created_at: datetime


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class RetrievalResult(BaseModel):
    document_id: UUID
    chunk_id: UUID
    filename: str
    content: str
    score: float
    metadata: dict


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievalResult]


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[dict]
    created_at: datetime
