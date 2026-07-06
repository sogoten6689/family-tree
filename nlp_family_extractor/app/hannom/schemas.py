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


class HannomTokenStatusResponse(BaseModel):
    configured: bool
    source: str
    preview: str | None = None
    token_length: int = 0
