from typing import Any, List
from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import crud
from app.models import models
from app.schemas import schemas
from app.core.database import get_db
from app.services.ssl_checker import check_ssl
from app.services.notifier import dispatch_alert, send_telegram_message, send_email

router = APIRouter()

# --- Public Site Endpoints ---

@router.get("/", response_model=List[schemas.SiteOut])
def read_sites(db: Session = Depends(get_db)) -> Any:
    """
    Retrieve all sites. Publicly accessible.
    """
    return crud.get_sites(db)


# --- Admin Site Endpoints ---

@router.post("/", response_model=schemas.SiteOut)
def create_site(
    *,
    db: Session = Depends(get_db),
    site_in: schemas.SiteCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new site and immediately check it. Admin only.
    """
    db_site = crud.create_site(db, site=site_in)
    
    # Immediately trigger SSL check
    try:
        result = check_ssl(db_site.hostname, db_site.port)
        db_site.status = result["status"]
        db_site.ssl_valid_from = result["ssl_valid_from"]
        db_site.ssl_valid_to = result["ssl_valid_to"]
        db_site.ssl_issuer = result["ssl_issuer"]
        db_site.last_error = result["last_error"]
        db_site.last_checked = result["last_checked"]
        db.commit()
        db.refresh(db_site)
    except Exception:
        # If check fails during creation, don't crash, just let the user see the unchecked/error state
        pass
        
    return db_site


@router.put("/{site_id}", response_model=schemas.SiteOut)
def update_site(
    site_id: str,
    site_in: schemas.SiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update site. Admin only.
    """
    site = crud.update_site(db, site_id=site_id, site_update=site_in)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.delete("/{site_id}")
def delete_site(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete site. Admin only.
    """
    success = crud.delete_site(db, site_id=site_id)
    if not success:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"status": "success", "message": "Site deleted"}


@router.post("/{site_id}/check", response_model=schemas.SiteOut)
def trigger_site_check(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Manually trigger an SSL check for a site and dispatch notifications if necessary.
    Admin only.
    """
    site = crud.get_site(db, site_id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
        
    # Perform SSL check
    result = check_ssl(site.hostname, site.port)
    
    # Update site details
    site.status = result["status"]
    site.ssl_valid_from = result["ssl_valid_from"]
    site.ssl_valid_to = result["ssl_valid_to"]
    site.ssl_issuer = result["ssl_issuer"]
    site.last_error = result["last_error"]
    site.last_checked = result["last_checked"]
    
    db.commit()
    db.refresh(site)
    
    # Determine if alert is needed
    should_alert = False
    days_remaining = 9999
    
    if site.status in ["expired", "error"]:
        should_alert = True
    elif site.ssl_valid_to:
        now = datetime.now(timezone.utc)
        delta = site.ssl_valid_to - now
        days_remaining = delta.days
        if days_remaining <= site.warning_days:
            site.status = "warning"
            should_alert = True
            db.commit()
            
    if should_alert:
        # Dispatch to all enabled global notification configs
        configs = crud.get_notification_configs(db)
        for config in configs:
            config_dict = {
                "channel_type": config.channel_type,
                "config_json": config.config_json,
                "is_enabled": config.is_enabled,
                "last_error": site.last_error
            }
            dispatch_alert(site.hostname, days_remaining, site.status, site.warning_days, config_dict)
            
    return site


# --- Site Manual Reordering ---

@router.post("/{site_id}/move-up", response_model=schemas.SiteOut)
def move_up(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Move a site up in the priority list. Admin only.
    """
    success = crud.move_site_up(db, site_id=site_id)
    if not success:
        # Might be already at the top, just return the site
        site = crud.get_site(db, site_id=site_id)
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        return site
    return crud.get_site(db, site_id=site_id)


@router.post("/{site_id}/move-down", response_model=schemas.SiteOut)
def move_down(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Move a site down in the priority list. Admin only.
    """
    success = crud.move_site_down(db, site_id=site_id)
    if not success:
        # Might be already at the bottom, just return the site
        site = crud.get_site(db, site_id=site_id)
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        return site
    return crud.get_site(db, site_id=site_id)


# --- Global Notification Config Endpoints ---

@router.get("/notifications/all", response_model=List[schemas.NotificationConfigOut])
def read_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get all global notification configs. Admin only.
    """
    return crud.get_notification_configs(db)


@router.post("/notifications/all", response_model=schemas.NotificationConfigOut)
def create_notification_config(
    config_in: schemas.NotificationConfigCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a global notification config. Admin only.
    """
    try:
        json.loads(config_in.config_json)
    except Exception:
        raise HTTPException(status_code=400, detail="config_json must be a valid JSON string")
    return crud.create_notification_config(db, config=config_in)


@router.put("/notifications/all/{config_id}", response_model=schemas.NotificationConfigOut)
def update_notification_config(
    config_id: str,
    config_in: schemas.NotificationConfigBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a global notification config. Admin only.
    """
    try:
        json.loads(config_in.config_json)
    except Exception:
        raise HTTPException(status_code=400, detail="config_json must be a valid JSON string")
    config = crud.update_notification_config(db, config_id=config_id, config_update=config_in)
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found")
    return config


@router.delete("/notifications/all/{config_id}")
def delete_notification_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a global notification config. Admin only.
    """
    success = crud.delete_notification_config(db, config_id=config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification config not found")
    return {"status": "success", "message": "Notification config deleted"}


@router.post("/notifications/all/{config_id}/test")
def test_notification_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send a test alert to a specific notification channel. Admin only.
    """
    config = crud.get_notification_config(db, config_id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found")
        
    try:
        cfg = json.loads(config.config_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid configuration JSON")
        
    success = False
    if config.channel_type == "telegram":
        bot_token = cfg.get("bot_token")
        chat_id = cfg.get("chat_id")
        thread_id = cfg.get("thread_id")
        if bot_token and chat_id:
            success = send_telegram_message(bot_token, chat_id, "тест\nTEST", thread_id)
    elif config.channel_type == "email":
        recipients_str = cfg.get("recipient_emails", "")
        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
        if recipients:
            success = send_email("тест / TEST", "<p>тест</p><p>TEST</p>", recipients, cfg)
            
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send test notification. Check bot token/chat ID or SMTP credentials."
        )
        
    return {"status": "success", "message": "Test notification sent successfully"}
