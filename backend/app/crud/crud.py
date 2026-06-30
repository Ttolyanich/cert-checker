from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.models import models
from app.schemas import schemas
from app.core.security import get_password_hash

# --- User CRUD ---
def get_user(db: Session, user_id: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: str, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]
        
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: str) -> bool:
    db_user = get_user(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False


# --- Site CRUD (With Ordering) ---
def get_site(db: Session, site_id: str) -> Optional[models.Site]:
    return db.query(models.Site).filter(models.Site.id == site_id).first()

def get_sites(db: Session) -> List[models.Site]:
    return db.query(models.Site).order_by(models.Site.order_index.asc()).all()

def create_site(db: Session, site: schemas.SiteCreate) -> models.Site:
    max_order = db.query(func.max(models.Site.order_index)).scalar()
    next_order = (max_order or 0) + 1
    
    db_site = models.Site(
        hostname=site.hostname,
        port=site.port,
        warning_days=site.warning_days,
        order_index=next_order
    )
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site

def update_site(db: Session, site_id: str, site_update: schemas.SiteUpdate) -> Optional[models.Site]:
    db_site = get_site(db, site_id)
    if not db_site:
        return None
    for key, value in site_update.model_dump(exclude_unset=True).items():
        setattr(db_site, key, value)
    db.commit()
    db.refresh(db_site)
    return db_site

def delete_site(db: Session, site_id: str) -> bool:
    db_site = get_site(db, site_id)
    if db_site:
        db.delete(db_site)
        db.commit()
        return True
    return False


# --- Site Manual Reordering Logic ---
def move_site_up(db: Session, site_id: str) -> bool:
    current_site = get_site(db, site_id)
    if not current_site:
        return False
        
    sibling = db.query(models.Site).filter(
        models.Site.order_index < current_site.order_index
    ).order_by(models.Site.order_index.desc()).first()
    
    if not sibling:
        return False
        
    current_site.order_index, sibling.order_index = sibling.order_index, current_site.order_index
    db.commit()
    return True

def move_site_down(db: Session, site_id: str) -> bool:
    current_site = get_site(db, site_id)
    if not current_site:
        return False
        
    sibling = db.query(models.Site).filter(
        models.Site.order_index > current_site.order_index
    ).order_by(models.Site.order_index.asc()).first()
    
    if not sibling:
        return False
        
    current_site.order_index, sibling.order_index = sibling.order_index, current_site.order_index
    db.commit()
    return True


# --- Notification Config CRUD ---
def get_notification_configs(db: Session) -> List[models.NotificationConfig]:
    return db.query(models.NotificationConfig).all()

def get_notification_config(db: Session, config_id: str) -> Optional[models.NotificationConfig]:
    return db.query(models.NotificationConfig).filter(models.NotificationConfig.id == config_id).first()

def create_notification_config(
    db: Session, config: schemas.NotificationConfigCreate
) -> models.NotificationConfig:
    db_config = models.NotificationConfig(
        channel_type=config.channel_type,
        config_json=config.config_json,
        is_enabled=config.is_enabled
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

def update_notification_config(
    db: Session, config_id: str, config_update: schemas.NotificationConfigBase
) -> Optional[models.NotificationConfig]:
    db_config = get_notification_config(db, config_id)
    if not db_config:
        return None
    for key, value in config_update.model_dump(exclude_unset=True).items():
        setattr(db_config, key, value)
    db.commit()
    db.refresh(db_config)
    return db_config

def delete_notification_config(db: Session, config_id: str) -> bool:
    db_config = get_notification_config(db, config_id)
    if db_config:
        db.delete(db_config)
        db.commit()
        return True
    return False
