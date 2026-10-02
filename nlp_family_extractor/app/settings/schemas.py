from pydantic import BaseModel, Field


class SettingItem(BaseModel):
    key: str
    masked_value: str | None = None
    configured: bool = False
    updated_at: str | None = None


class SettingUpsertRequest(BaseModel):
    value: str = Field(min_length=1)


class OcrEngineItem(BaseModel):
    name: str
    label: str
    enabled: bool
    ready: bool
    ready_reason: str | None = None


class OcrEngineConfig(BaseModel):
    min_enabled: int
    engines: list[OcrEngineItem]


class OcrEngineUpdateRequest(BaseModel):
    enabled: list[str]


class TextEngineConfig(OcrEngineConfig):
    load_error: str | None = None
