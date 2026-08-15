from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field


# ---------- Instruments ----------
class InstrumentBase(BaseModel):
    isin: str = Field(min_length=12, max_length=12)
    yahoo_symbol: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1)
    exchange: str | None = None
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    region: str | None = None
    is_active: bool = True
    is_benchmark: bool = False


class InstrumentCreate(InstrumentBase):
    pass


class InstrumentUpdate(BaseModel):
    isin: str | None = Field(default=None, min_length=12, max_length=12)
    yahoo_symbol: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = None
    exchange: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    region: str | None = None
    is_active: bool | None = None
    is_benchmark: bool | None = None


class InstrumentResponse(InstrumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Lookup (recherche automatique) ----------
class LookupRequest(BaseModel):
    query: str = Field(min_length=2, max_length=20)


class LookupResponse(BaseModel):
    isin: str | None
    yahoo_symbol: str
    name: str
    exchange: str | None
    currency: str
    region: str | None
    message: str


# ---------- Prix ----------
class PriceImportResult(BaseModel):
    inserted: int
    updated: int
    total: int


class PerformanceResponse(BaseModel):
    instrument_id: int
    last_close: float | None
    sma200: float | None
    above_sma200: bool | None
    perf_1m: float | None
    perf_3m: float | None
    perf_6m: float | None
    perf_12m: float | None
    total_points: int


class PriceUpdateRequest(BaseModel):
    force_full: bool = False
    instrument_id: int | None = None


class PriceUpdateResult(BaseModel):
    instrument_id: int
    name: str
    yahoo_symbol: str
    inserted: int
    updated: int
    total: int
    status: str
    message: str


# ---------- Settings ----------
class SettingUpdate(BaseModel):
    setting_key: str
    setting_value: str


class SettingResponse(BaseModel):
    setting_key: str
    setting_value: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Signaux ----------
class SignalResponse(BaseModel):
    id: int
    signal_date: date
    selected_instrument_id: int | None
    previous_instrument_id: int | None
    signal_type: str
    leader_score: float | None
    second_score: float | None
    score_gap: float | None
    leader_close: float | None
    leader_sma200: float | None
    leader_above_sma200: bool | None
    threshold_used: float | None
    calculation_details_json: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- IA ----------
class AICommentaryRequest(BaseModel):
    force: bool = False


class AICommentaryResponse(BaseModel):
    id: int
    monthly_signal_id: int | None
    provider: str
    model_name: str | None
    summary: str
    decision_explained: str
    risk_note: str | None
    raw_json: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    is_admin: bool = False


class UserListItem(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)