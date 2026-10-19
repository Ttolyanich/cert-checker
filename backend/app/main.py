import os
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text, inspect

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models import models
from app.api.endpoints import auth, users, sites, zabbix
from app.services.ssl_checker import check_ssl
from app.services.notifier import dispatch_alert

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def check_single_site(site_id: str):
    """
    Worker function to check SSL certificate for a single site and update status.
    """
    db = SessionLocal()
    try:
        site = db.query(models.Site).filter(models.Site.id == site_id).first()
        if not site:
            return
        
        result = check_ssl(site.hostname, site.port)
        site.status = result["status"]
        site.ssl_valid_from = result["ssl_valid_from"]
        site.ssl_valid_to = result["ssl_valid_to"]
        site.ssl_issuer = result["ssl_issuer"]
        site.last_error = result["last_error"]
        site.last_checked = result["last_checked"]
        
        should_alert = False
        alert_level = None
        days_remaining = 9999
        now = datetime.now(timezone.utc)
        
        if site.status in ["expired", "error"]:
            should_alert = True
            alert_level = site.status
        elif site.ssl_valid_to:
            valid_to = site.ssl_valid_to
            if valid_to.tzinfo is None:
                valid_to = valid_to.replace(tzinfo=timezone.utc)
            delta = valid_to - now
            days_remaining = delta.days
            if days_remaining <= site.critical_days:
                site.status = "critical"
                should_alert = True
                alert_level = "critical"
            elif days_remaining <= site.warning_days:
                site.status = "warning"
                should_alert = True
                alert_level = "warning"
        
        # Alert throttling / deduplication logic:
        # Send alert if level changed OR if it has been at least 3 days since the last alert of same level
        is_level_changed = (site.last_alert_level != alert_level)
        is_cooldown_expired = (
            site.last_alert_at is None or 
            (now - site.last_alert_at.replace(tzinfo=timezone.utc if site.last_alert_at.tzinfo is None else None) > timedelta(days=3))
        )
        
        if should_alert and (is_level_changed or is_cooldown_expired):
            configs = db.query(models.NotificationConfig).filter(models.NotificationConfig.is_enabled == True).all()
            if configs:
                logger.info(f"Dispatching alerts for {site.hostname} (level: {alert_level}, days left: {days_remaining})")
                for config in configs:
                    config_dict = {
                        "channel_type": config.channel_type,
                        "config_json": config.config_json,
                        "is_enabled": config.is_enabled,
                        "last_error": site.last_error,
                        "alert_level": alert_level
                    }
                    try:
                        dispatch_alert(site.hostname, days_remaining, site.status, site.warning_days, config_dict)
                    except Exception as notif_err:
                        logger.error(f"Failed to send alert via {config.channel_type}: {notif_err}")
                
                # Update alert tracking
                site.last_alert_at = now
                site.last_alert_level = alert_level
        elif not should_alert:
            # Certificate is healthy/valid: reset alert level so if it drops again we notify immediately
            site.last_alert_level = None

        db.commit()
    except Exception as e:
        logger.error(f"Error checking site id {site_id}: {e}")
        db.rollback()
    finally:
        db.close()


def check_all_sites_job():
    """
    Concurrent background job that checks SSL certificates for all sites in the DB.
    """
    logger.info("Starting background concurrent SSL check for all registered sites...")
    db = SessionLocal()
    try:
        site_ids = [s.id for s in db.query(models.Site.id).all()]
    except Exception as e:
        logger.error(f"Database error reading sites list: {e}")
        return
    finally:
        db.close()

    if not site_ids:
        logger.info("No sites configured for SSL check.")
        return

    logger.info(f"Checking {len(site_ids)} sites concurrently...")
    with ThreadPoolExecutor(max_workers=min(len(site_ids), 12)) as executor:
        executor.map(check_single_site, site_ids)
    logger.info("Background SSL check completed.")


def check_and_restore_database():
    """
    Checks if /data/cert_checker.db is missing or empty, and restores from candidate locations if available.
    """
    primary_db = "/data/cert_checker.db"
    try:
        os.makedirs("/data", exist_ok=True)
        if not os.path.exists(primary_db) or os.path.getsize(primary_db) == 0:
            candidates = [
                "/data/data/cert_checker.db",
                "/app/cert_checker.db",
                "./cert_checker.db",
            ]
            for cand in candidates:
                if os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(primary_db) and os.path.getsize(cand) > 0:
                    logger.info(f"Auto-restoring database from {cand} to {primary_db}...")
                    import shutil
                    shutil.copy2(cand, primary_db)
                    break
    except Exception as e:
        logger.warning(f"Failed to check/restore database: {e}")

def run_database_migrations():
    """
    Performs auto-migrations for missing columns across SQLite database versions.
    """
    check_and_restore_database()
    logger.info("Checking database schema and migrations...")
    Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        
        # 1. Sites table migrations
        if "sites" in inspector.get_table_names():
            site_cols = [c["name"] for c in inspector.get_columns("sites")]
            if "critical_days" not in site_cols:
                logger.info("Migrating: adding critical_days to sites table...")
                conn.execute(text("ALTER TABLE sites ADD COLUMN critical_days INTEGER NOT NULL DEFAULT 7"))
                conn.commit()
            if "last_alert_at" not in site_cols:
                logger.info("Migrating: adding last_alert_at to sites table...")
                conn.execute(text("ALTER TABLE sites ADD COLUMN last_alert_at DATETIME"))
                conn.commit()
            if "last_alert_level" not in site_cols:
                logger.info("Migrating: adding last_alert_level to sites table...")
                conn.execute(text("ALTER TABLE sites ADD COLUMN last_alert_level VARCHAR(50)"))
                conn.commit()
                
        # 2. Users table migrations
        if "users" in inspector.get_table_names():
            user_cols = [c["name"] for c in inspector.get_columns("users")]
            if "role" not in user_cols:
                logger.info("Migrating: adding role to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'admin'"))
                conn.commit()
            if "auth_source" not in user_cols:
                logger.info("Migrating: adding auth_source to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN auth_source VARCHAR(50) NOT NULL DEFAULT 'local'"))
                conn.commit()

    # Create default superuser if none exists
    db = SessionLocal()
    try:
        admin_user = db.query(models.User).filter(models.User.username == settings.FIRST_SUPERUSER_USERNAME).first()
        if not admin_user:
            logger.info(f"Creating default superuser: {settings.FIRST_SUPERUSER_USERNAME}")
            new_admin = models.User(
                username=settings.FIRST_SUPERUSER_USERNAME,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                full_name="Global Administrator",
                role="admin",
                auth_source="local",
                is_active=True
            )
            db.add(new_admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    run_database_migrations()
    
    logger.info("Starting background scheduler...")
    scheduler.add_job(check_all_sites_job, 'interval', hours=12, id='ssl_check_job')
    scheduler.add_job(check_all_sites_job, 'date', run_date=datetime.now() + timedelta(seconds=5))
    scheduler.start()
    
    yield
    
    # Shutdown actions
    logger.info("Shutting down background scheduler...")
    if scheduler.running:
        scheduler.shutdown(wait=False)


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(sites.router, prefix=f"{settings.API_V1_STR}/sites", tags=["sites"])
app.include_router(zabbix.router, prefix=f"{settings.API_V1_STR}/zabbix", tags=["zabbix"])

# --- All-in-One: Serve Built React Frontend SPA if present ---
app_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/app
backend_dir = os.path.dirname(app_dir) # .../backend
static_dist_dirs = [
    os.path.join(backend_dir, "static_dist"),
    os.path.join(os.path.dirname(backend_dir), "frontend", "dist"),
    "/app/static_dist"
]

dist_path = None
for candidate in static_dist_dirs:
    if os.path.exists(candidate) and os.path.isdir(candidate):
        dist_path = candidate
        break

if dist_path:
    logger.info(f"Serving static frontend SPA from: {dist_path}")
    assets_dir = os.path.join(dist_path, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_frontend(full_path: str):
        # Do not catch API or OpenAPI routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        candidate_file = os.path.join(dist_path, full_path)
        if os.path.isfile(candidate_file):
            return FileResponse(candidate_file)
            
        index_file = os.path.join(dist_path, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
            
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
