import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8)


class JurisdictionOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    scope_type: str

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    badge_number: str | None
    department: str | None
    role_code: str
    role_name: str
    permissions: list[str]
    jurisdictions: list[JurisdictionOut]
