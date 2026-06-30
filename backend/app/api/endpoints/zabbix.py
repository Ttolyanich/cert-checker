import os
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import models

router = APIRouter()

# Get token from environment or use a default one
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN", "zabbix_secret_token")

def verify_zabbix_token(token: str = Query(...)):
    """
    Dependency to verify the Zabbix API token.
    """
    if token != ZABBIX_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Zabbix token"
        )
    return token


@router.get("/discovery")
def zabbix_lld_discovery(
    db: Session = Depends(get_db),
    token: str = Depends(verify_zabbix_token)
) -> Any:
    """
    Low-Level Discovery (LLD) endpoint for Zabbix.
    Returns a flat list of all monitored sites.
    """
    sites = db.query(models.Site).order_by(models.Site.order_index.asc()).all()
    lld_data = []
    for site in sites:
        lld_data.append({
            "{#SITE_ID}": site.id,
            "{#SITE_HOST}": site.hostname,
            "{#SITE_PORT}": site.port,
        })
    return lld_data


@router.get("/metrics")
def zabbix_metrics(
    host: str = Query(..., description="The hostname of the monitored site"),
    port: int = Query(443, description="The port of the monitored site"),
    db: Session = Depends(get_db),
    token: str = Depends(verify_zabbix_token)
) -> Any:
    """
    Returns metrics for a specific site.
    Zabbix will parse this JSON using JSONPath preprocessing.
    """
    site = db.query(models.Site).filter(
        models.Site.hostname == host,
        models.Site.port == port
    ).first()
    
    if not site:
        raise HTTPException(
            status_code=404,
            detail=f"Site {host}:{port} not found in monitoring list"
        )
        
    days_left = -999  # default error/unchecked value
    if site.ssl_valid_to:
        valid_to = site.ssl_valid_to
        if valid_to.tzinfo is None:
            valid_to = valid_to.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = valid_to - now
        days_left = delta.days

    return {
        "hostname": site.hostname,
        "port": site.port,
        "status": site.status,
        "days_left": days_left,
        "warning_days": site.warning_days,
        "error": site.last_error or "",
        "last_checked": site.last_checked.isoformat() if site.last_checked else None
    }
