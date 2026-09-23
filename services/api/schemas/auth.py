import uuid

from pydantic import BaseModel


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


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


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
