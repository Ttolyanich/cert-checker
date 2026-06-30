from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta
import logging

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

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
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


# --- Background SSL Checker Job ---
def check_all_sites_job():
    """
    Background job that checks SSL certificates for all sites in the DB
    and dispatches alerts if needed.
    """
    logger.info("Starting background SSL check for all registered sites...")
    db = SessionLocal()
    try:
        sites_list = db.query(models.Site).all()
        logger.info(f"Found {len(sites_list)} sites to check.")
        
        for site in sites_list:
            try:
                logger.info(f"Checking {site.hostname}:{site.port}...")
                result = check_ssl(site.hostname, site.port)
                
                # Update database
                site.status = result["status"]
                site.ssl_valid_from = result["ssl_valid_from"]
                site.ssl_valid_to = result["ssl_valid_to"]
                site.ssl_issuer = result["ssl_issuer"]
                site.last_error = result["last_error"]
                site.last_checked = result["last_checked"]
                
                db.commit()
                
                # Determine alert triggers
                should_alert = False
                days_remaining = 9999
                
                if site.status in ["expired", "error"]:
                    should_alert = True
                elif site.ssl_valid_to:
                    valid_to = site.ssl_valid_to
                    if valid_to.tzinfo is None:
                        valid_to = valid_to.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    delta = valid_to - now
                    days_remaining = delta.days
                    if days_remaining <= site.warning_days:
                        site.status = "warning"
                        should_alert = True
                        db.commit()
                
                if should_alert:
                    # Retrieve global notification configs
                    configs = db.query(models.NotificationConfig).all()
                    
                    for config in configs:
                        config_dict = {
                            "channel_type": config.channel_type,
                            "config_json": config.config_json,
                            "is_enabled": config.is_enabled,
                            "last_error": site.last_error
                        }
                        dispatch_alert(site.hostname, days_remaining, site.status, site.warning_days, config_dict)
                        
            except Exception as e:
                logger.error(f"Error checking site {site.hostname}: {e}")
                
        logger.info("Background SSL check completed.")
    except Exception as e:
        logger.error(f"Database error in background job: {e}")
    finally:
        db.close()


# --- App Lifecycle events ---
scheduler = BackgroundScheduler()

@app.on_event("startup")
def on_startup():
    # 1. Create database tables if they don't exist
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Create default superuser if it doesn't exist
    db = SessionLocal()
    try:
        admin_user = db.query(models.User).filter(models.User.username == settings.FIRST_SUPERUSER_USERNAME).first()
        if not admin_user:
            logger.info(f"Creating default superuser: {settings.FIRST_SUPERUSER_USERNAME}")
            new_admin = models.User(
                username=settings.FIRST_SUPERUSER_USERNAME,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                full_name="Global Administrator",
                is_active=True
            )
            db.add(new_admin)
            db.commit()
    finally:
        db.close()
        
    # 3. Start background scheduler
    logger.info("Starting background scheduler...")
    scheduler.add_job(check_all_sites_job, 'interval', hours=12, id='ssl_check_job')
    # Run first check shortly after startup (e.g., 10 seconds)
    scheduler.add_job(check_all_sites_job, 'date', run_date=datetime.now() + timedelta(seconds=10))
    scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    logger.info("Shutting down background scheduler...")
    scheduler.shutdown()
