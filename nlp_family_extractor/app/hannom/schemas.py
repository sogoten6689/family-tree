from pydantic import BaseModel, Field


class HannomFetchTokenRequest(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=255)


class HannomFetchTokenResponse(BaseModel):
    token: str
    token_preview: str
    token_length: int
    source: str
    login_path: str
    username: str
    message: str


class HannomCredentialsUpdateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class HannomCredentialsStatusResponse(BaseModel):
    configured: bool
    username: str | None = None
    has_password: bool = False
    token_preview: str | None = None
    token_expires_at: str | None = None
    last_login_at: str | None = None
    last_error: str | None = None


class HannomTokenStatusResponse(BaseModel):
    configured: bool
    source: str
    preview: str | None = None
    token_length: int = 0
    expires_at: str | None = None
    username: str | None = None
    last_login_at: str | None = None
    last_error: str | None = None
