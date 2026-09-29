from pydantic import BaseModel, Field


class SettingItem(BaseModel):
    key: str
    masked_value: str | None = None
    configured: bool = False
    updated_at: str | None = None


class SettingUpsertRequest(BaseModel):
    value: str = Field(min_length=1)
