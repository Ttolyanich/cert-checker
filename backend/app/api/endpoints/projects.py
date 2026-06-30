from typing import Any, List, Optional
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
from app.services.notifier import dispatch_alert

router = APIRouter()

# --- Project Endpoints ---

@router.get("/", response_model=List[schemas.ProjectOut])
def read_projects(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve projects.
    Global Admin sees all. Others see only projects where they have project or zone roles.
    """
    if current_user.global_role == "admin":
        return crud.get_projects(db, skip=skip, limit=limit)
        
    # Filter projects for regular users
    all_projects = crud.get_projects(db, skip=0, limit=1000)
    accessible_projects = []
    
    for project in all_projects:
        # Check if user has direct project access
        if crud.check_user_access_project(db, current_user, project.id, require_admin=False):
            accessible_projects.append(project)
            continue
            
        # Check if user has access to any zone in this project
        for zone in project.zones:
            if db.query(models.UserZoneRole).filter(
                models.UserZoneRole.user_id == current_user.id,
                models.UserZoneRole.zone_id == zone.id
            ).first():
                accessible_projects.append(project)
                break
                
    return accessible_projects[skip : skip + limit]


@router.post("/", response_model=schemas.ProjectOut)
def create_project(
    *,
    db: Session = Depends(get_db),
    project_in: schemas.ProjectCreate,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new project. Only Global Admin.
    """
    project = crud.get_project_by_name(db, name=project_in.name)
    if project:
        raise HTTPException(status_code=400, detail="Project with this name already exists")
    return crud.create_project(db, project=project_in)


@router.get("/{project_id}", response_model=schemas.ProjectDetailOut)
def read_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get project by ID. Includes accessible zones.
    """
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Check access
    is_global_admin = current_user.global_role == "admin"
    has_project_access = crud.check_user_access_project(db, current_user, project_id, require_admin=False)
    
    if not is_global_admin and not has_project_access:
        # Check if they have access to at least one zone. If not, deny.
        accessible_zones = [
            z for z in project.zones 
            if crud.check_user_access_zone(db, current_user, z.id, require_admin=False)
        ]
        if not accessible_zones:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        # Return project with only accessible zones
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at,
            "zones": accessible_zones
        }
        
    return project


@router.put("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: str,
    project_in: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update project. Global Admin or Project Admin.
    """
    if not crud.check_user_access_project(db, current_user, project_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    project = crud.update_project(db, project_id=project_id, project_update=project_in)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Delete project. Only Global Admin.
    """
    success = crud.delete_project(db, project_id=project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "message": "Project deleted"}


# --- Zone Endpoints ---

@router.post("/{project_id}/zones", response_model=schemas.ZoneOut)
def create_zone(
    project_id: str,
    zone_in: schemas.ZoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create zone. Global Admin or Project Admin of the project.
    """
    if zone_in.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    if not crud.check_user_access_project(db, current_user, project_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_zone(db, zone=zone_in)


@router.get("/zones/{zone_id}", response_model=schemas.ZoneDetailOut)
def read_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get zone by ID. Includes sites.
    """
    if not crud.check_user_access_zone(db, current_user, zone_id, require_admin=False):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    zone = crud.get_zone(db, zone_id=zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.put("/zones/{zone_id}", response_model=schemas.ZoneOut)
def update_zone(
    zone_id: str,
    zone_in: schemas.ZoneUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update zone. Global Admin, Project Admin, or Zone Admin.
    """
    if not crud.check_user_access_zone(db, current_user, zone_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    zone = crud.update_zone(db, zone_id=zone_id, zone_update=zone_in)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.delete("/zones/{zone_id}")
def delete_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete zone. Global Admin or Project Admin.
    """
    zone = crud.get_zone(db, zone_id=zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    if not crud.check_user_access_project(db, current_user, zone.project_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_zone(db, zone_id=zone_id)
    return {"status": "success", "message": "Zone deleted"}


# --- Site Endpoints ---

@router.post("/zones/{zone_id}/sites", response_model=schemas.SiteOut)
def create_site(
    zone_id: str,
    site_in: schemas.SiteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create site in zone. Global Admin, Project Admin, or Zone Admin.
    """
    if site_in.zone_id != zone_id:
        raise HTTPException(status_code=400, detail="Zone ID mismatch")
    if not crud.check_user_access_zone(db, current_user, zone_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.create_site(db, site=site_in)


@router.put("/sites/{site_id}", response_model=schemas.SiteOut)
def update_site(
    site_id: str,
    site_in: schemas.SiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update site. Global Admin, Project Admin, or Zone Admin.
    """
    site = crud.get_site(db, site_id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not crud.check_user_access_zone(db, current_user, site.zone_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.update_site(db, site_id=site_id, site_update=site_in)


@router.delete("/sites/{site_id}")
def delete_site(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete site. Global Admin, Project Admin, or Zone Admin.
    """
    site = crud.get_site(db, site_id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not crud.check_user_access_zone(db, current_user, site.zone_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_site(db, site_id=site_id)
    return {"status": "success", "message": "Site deleted"}


@router.post("/sites/{site_id}/check", response_model=schemas.SiteOut)
def trigger_site_check(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Manually trigger an SSL check for a site and dispatch notifications if necessary.
    """
    site = crud.get_site(db, site_id=site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
        
    # Check read access to zone
    if not crud.check_user_access_zone(db, current_user, site.zone_id, require_admin=False):
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
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
        # Find notification configs for this Zone or Parent Project
        configs = []
        # 1. Zone configs
        configs.extend(crud.get_notification_configs(db, zone_id=site.zone_id))
        # 2. Project configs
        configs.extend(crud.get_notification_configs(db, project_id=site.zone.project_id))
        
        for config in configs:
            # We pass a dictionary to dispatch_alert representing the config
            config_dict = {
                "channel_type": config.channel_type,
                "config_json": config.config_json,
                "is_enabled": config.is_enabled,
                "last_error": site.last_error
            }
            dispatch_alert(site.hostname, days_remaining, site.status, site.warning_days, config_dict)
            
    return site


# --- Notification Config Endpoints ---

@router.get("/project/{project_id}/notifications", response_model=List[schemas.NotificationConfigOut])
def read_project_notifications(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get notification configs for a project.
    """
    if not crud.check_user_access_project(db, current_user, project_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_notification_configs(db, project_id=project_id)


@router.get("/zone/{zone_id}/notifications", response_model=List[schemas.NotificationConfigOut])
def read_zone_notifications(
    zone_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get notification configs for a zone.
    """
    if not crud.check_user_access_zone(db, current_user, zone_id, require_admin=True):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_notification_configs(db, zone_id=zone_id)


@router.post("/notifications", response_model=schemas.NotificationConfigOut)
def create_notification_config(
    config_in: schemas.NotificationConfigCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a notification config for a project or zone.
    """
    if config_in.project_id:
        if not crud.check_user_access_project(db, current_user, config_in.project_id, require_admin=True):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    elif config_in.zone_id:
        if not crud.check_user_access_zone(db, current_user, config_in.zone_id, require_admin=True):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    else:
        raise HTTPException(status_code=400, detail="Either project_id or zone_id must be provided")
        
    # Validate JSON config
    try:
        json.loads(config_in.config_json)
    except Exception:
        raise HTTPException(status_code=400, detail="config_json must be a valid JSON string")
        
    return crud.create_notification_config(db, config=config_in)


@router.put("/notifications/{config_id}", response_model=schemas.NotificationConfigOut)
def update_notification_config(
    config_id: str,
    config_in: schemas.NotificationConfigBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a notification config.
    """
    db_config = db.query(models.NotificationConfig).filter(models.NotificationConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Notification config not found")
        
    # Check permissions
    if db_config.project_id:
        if not crud.check_user_access_project(db, current_user, db_config.project_id, require_admin=True):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    elif db_config.zone_id:
        if not crud.check_user_access_zone(db, current_user, db_config.zone_id, require_admin=True):
            raise HTTPException(status_code=403, detail="Not enough permissions")
            
    try:
        json.loads(config_in.config_json)
    except Exception:
        raise HTTPException(status_code=400, detail="config_json must be a valid JSON string")
        
    return crud.update_notification_config(db, config_id=config_id, config_update=config_in)


@router.delete("/notifications/{config_id}")
def delete_notification_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a notification config.
    """
    db_config = db.query(models.NotificationConfig).filter(models.NotificationConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Notification config not found")
        
    # Check permissions
    if db_config.project_id:
        if not crud.check_user_access_project(db, current_user, db_config.project_id, require_admin=True):
            raise HTTPException(status_code=403, detail="Not enough permissions")
    elif db_config.zone_id:
        if not crud.check_user_access_zone(db, current_user, db_config.zone_id, require_admin=True):
            raise HTTPException(status_code=403, detail="Not enough permissions")
            
    crud.delete_notification_config(db, config_id=config_id)
    return {"status": "success", "message": "Notification config deleted"}
