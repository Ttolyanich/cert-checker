from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.api import deps
from app.crud import crud
from app.schemas import schemas
from app.models import models
from app.services.ldap_auth import authenticate_ldap

router = APIRouter()

@router.get("/config")
def get_auth_config() -> Any:
    """
    Returns public auth configurations, such as whether LDAP is enabled.
    """
    return {
        "ldap_enabled": settings.LDAP_ENABLED,
        "ldap_domain": settings.LDAP_DOMAIN if settings.LDAP_ENABLED else None,
        "project_name": settings.PROJECT_NAME
    }

@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login: supports both local accounts and Active Directory / LDAP.
    """
    input_username = form_data.username.strip()
    
    # 1. Try local authentication first
    user = db.query(models.User).filter(
        func.lower(models.User.username) == input_username.lower()
    ).first()

    if user and user.auth_source != "ldap" and user.hashed_password:
        if security.verify_password(form_data.password, user.hashed_password):
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user account",
                )
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            return {
                "access_token": security.create_access_token(
                    user.id, expires_delta=access_token_expires
                ),
                "token_type": "bearer",
            }

    # 2. Try Active Directory / LDAP if enabled
    if settings.LDAP_ENABLED:
        ldap_ok, resolved_username, ad_role, display_name, ldap_err = authenticate_ldap(
            input_username, form_data.password
        )
        if ldap_ok:
            # Look up user by resolved username or input username
            candidates = [input_username.lower()]
            if resolved_username:
                candidates.append(resolved_username.lower())
                if "@" in resolved_username:
                    candidates.append(resolved_username.split("@")[0].lower())

            db_user = db.query(models.User).filter(
                func.lower(models.User.username).in_(candidates)
            ).first()

            if not db_user:
                db_user = models.User(
                    username=resolved_username.lower() if resolved_username else input_username.lower(),
                    hashed_password=None,
                    full_name=display_name or input_username,
                    role=ad_role or "admin",
                    auth_source="ldap",
                    is_active=True
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
            else:
                db_user.auth_source = "ldap"
                if display_name:
                    db_user.full_name = display_name
                if ad_role:
                    db_user.role = ad_role
                db.commit()
                db.refresh(db_user)

            if not db_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User account is deactivated in Cert-Checker",
                )

            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            return {
                "access_token": security.create_access_token(
                    db_user.id, expires_delta=access_token_expires
                ),
                "token_type": "bearer",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ldap_err or "Неверный корпоративный email/логин или пароль Active Directory",
            )

    hint = " (Доменная авторизация Active Directory отключена в .env)" if ("@" in input_username or "\\" in input_username) else ""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Неверное имя пользователя или пароль{hint}",
    )

@router.get("/me", response_model=schemas.UserOut)
def read_user_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user profile and role.
    """
    return current_user
