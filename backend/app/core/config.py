import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "SSL Cert Checker"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "SUPER_SECRET_KEY_CHANGE_ME_IN_PRODUCTION_1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ZABBIX_TOKEN: str = "zabbix_secret_token"
    
    # Database
    DATABASE_URL: str = "sqlite:///./cert_checker.db"
    
    # Initial Admin Account
    FIRST_SUPERUSER_USERNAME: str = "admin"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"
    
    # Active Directory / LDAP Domain Authentication
    LDAP_ENABLED: bool = False
    LDAP_SERVER: Optional[str] = None         # e.g. "ldap://10.11.4.254:389" or "ldaps://..."
    LDAP_DOMAIN: Optional[str] = None         # e.g. "corp.local"
    LDAP_BASE_DN: Optional[str] = None        # e.g. "DC=corp,DC=local"
    LDAP_REQUIRED_GROUP: Optional[str] = None # e.g. "Domain Users" (if set, user must belong to this group)
    LDAP_ADMIN_GROUP: Optional[str] = None    # e.g. "Domain Admins" (members get role="admin")
    LDAP_ADMIN_USERS: Optional[str] = None    # e.g. "admin,sysadmin@corp.local" (comma-separated logins)
    LDAP_BIND_USER: Optional[str] = None      # e.g. "CN=svc_ldap,OU=Service,DC=corp,DC=local"
    LDAP_BIND_PASSWORD: Optional[str] = None
    LDAP_NESTED_GROUPS: bool = True           # Support LDAP_MATCHING_RULE_IN_CHAIN for nested groups
    
    # SMTP Settings (for Email notifications)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = "noreply@certchecker.local"
    EMAILS_FROM_NAME: str = "Cert-Checker Alert"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()
