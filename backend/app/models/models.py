import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Site(Base):
    __tablename__ = "sites"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    hostname = Column(String(255), nullable=False, index=True)
    port = Column(Integer, default=443, nullable=False)
    warning_days = Column(Integer, default=14, nullable=False)
    order_index = Column(Integer, default=0, nullable=False) # Used for manual sorting
    status = Column(String(50), default="unchecked", nullable=False) # "valid", "warning", "expired", "error", "unchecked"
    ssl_valid_from = Column(DateTime, nullable=True)
    ssl_valid_to = Column(DateTime, nullable=True)
    ssl_issuer = Column(String(255), nullable=True)
    last_error = Column(Text, nullable=True)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    channel_type = Column(String(50), nullable=False) # "email", "telegram"
    config_json = Column(Text, nullable=False) # JSON configuration (bot_token, chat_id, thread_id, etc.)
    is_enabled = Column(Boolean, default=True, nullable=False)
