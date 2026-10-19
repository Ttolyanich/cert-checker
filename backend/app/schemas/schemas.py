from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None


# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str = "admin"
    auth_source: str = "local"
    is_active: bool = True

class UserCreate(BaseModel):
    username: str
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "admin"
    auth_source: str = "local"
    is_active: bool = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    auth_source: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Site Schemas ---
class SiteBase(BaseModel):
    hostname: str
    port: int = 443
    warning_days: int = 14
    critical_days: int = 7

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    hostname: Optional[str] = None
    port: Optional[int] = None
    warning_days: Optional[int] = None
    critical_days: Optional[int] = None

class SiteOut(SiteBase):
    id: str
    order_index: int
    status: str
    ssl_valid_from: Optional[datetime] = None
    ssl_valid_to: Optional[datetime] = None
    ssl_issuer: Optional[str] = None
    last_error: Optional[str] = None
    last_checked: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None
    last_alert_level: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Notification Config Schemas ---
class NotificationConfigBase(BaseModel):
    channel_type: str # "email", "telegram"
    config_json: str  # JSON string containing configuration
    is_enabled: bool = True

class NotificationConfigCreate(NotificationConfigBase):
    pass

class NotificationConfigOut(NotificationConfigBase):
    id: str

    class Config:
        from_attributes = True
