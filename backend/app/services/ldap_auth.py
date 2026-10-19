import logging
from typing import Tuple, Optional, Set
from app.core.config import settings

logger = logging.getLogger(__name__)

def authenticate_ldap(username: str, password: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Authenticates a user against Active Directory / LDAP.
    Returns:
        (success: bool,
         resolved_username: Optional[str],
         role: Optional[str],
         display_name: Optional[str],
         error_message: Optional[str])
    """
    if not settings.LDAP_ENABLED:
        return False, None, None, None, "LDAP authentication is disabled."

    if not username or not password:
        return False, None, None, None, "Username and password are required."

    try:
        from ldap3 import Server, Connection, ALL, SUBTREE
        from ldap3.utils.conv import escape_filter_chars
    except ImportError:
        logger.error("ldap3 package is not installed. Please install ldap3>=2.9.1")
        return False, None, None, None, "LDAP library is not installed on the server."

    server_uri = (settings.LDAP_SERVER or "").strip()
    base_dn = (settings.LDAP_BASE_DN or "").strip()
    ldap_domain = (settings.LDAP_DOMAIN or "").strip().lower()
    bind_user = (settings.LDAP_BIND_USER or "").strip()
    bind_password = settings.LDAP_BIND_PASSWORD or ""
    req_group = (settings.LDAP_REQUIRED_GROUP or "").strip()
    admin_group = (settings.LDAP_ADMIN_GROUP or "").strip()

    if not server_uri or not base_dn:
        return False, None, None, None, "LDAP configuration is incomplete (LDAP_SERVER or LDAP_BASE_DN missing)."

    clean_id = username.strip()
    clean_user = clean_id
    if "\\" in clean_user:
        clean_user = clean_user.split("\\", 1)[1]
    if "@" in clean_user:
        clean_user = clean_user.split("@", 1)[0]

    try:
        use_ssl = server_uri.lower().startswith("ldaps://")
        server = Server(server_uri, use_ssl=use_ssl, get_info=ALL, connect_timeout=5)

        user_dn = None
        user_entry = None

        # Strategy 1: If service bind user is specified, bind as service account, find user DN, then bind as user
        if bind_user and bind_password:
            try:
                service_conn = Connection(server, user=bind_user, password=bind_password, auto_bind=True)
            except Exception as e:
                logger.error(f"[LDAP] Service bind failed for {bind_user}: {e}")
                return False, None, None, None, f"Service account bind error: {e}"

            safe_id = escape_filter_chars(clean_id)
            safe_user = escape_filter_chars(clean_user)
            upn_cand = escape_filter_chars(f"{clean_user}@{ldap_domain}") if ldap_domain else safe_id

            search_filter = (
                f"(&(objectCategory=person)(objectClass=user)"
                f"(|(mail={safe_id})(userPrincipalName={safe_id})(userPrincipalName={upn_cand})"
                f"(sAMAccountName={safe_id})(sAMAccountName={safe_user})))"
            )

            service_conn.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['distinguishedName', 'sAMAccountName', 'userPrincipalName', 'displayName', 'mail', 'memberOf']
            )

            if not service_conn.entries:
                service_conn.unbind()
                return False, None, None, None, "User not found in Active Directory."

            user_entry = service_conn.entries[0]
            user_dn = str(user_entry.entry_dn if hasattr(user_entry, 'entry_dn') else user_entry.distinguishedName)
            service_conn.unbind()

            # Now verify user credentials
            try:
                user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
                if not user_conn.bound:
                    return False, None, None, None, "Invalid Active Directory password."
                user_conn.unbind()
            except Exception:
                return False, None, None, None, "Invalid Active Directory credentials."

        # Strategy 2: Direct bind using UPN or domain\username
        else:
            user_conn = None
            direct_candidates = []
            if "@" in clean_id:
                direct_candidates.append(clean_id)
            if "\\" in clean_id:
                direct_candidates.append(clean_id)

            domain_short = ldap_domain.split(".")[0].upper() if ldap_domain else ""
            if domain_short:
                direct_candidates.append(f"{domain_short}\\{clean_user}")
            if ldap_domain:
                direct_candidates.append(f"{clean_user}@{ldap_domain}")
            direct_candidates.append(clean_user)

            for cand in dict.fromkeys([c for c in direct_candidates if c]):
                try:
                    tc = Connection(server, user=cand, password=password, auto_bind=True)
                    if tc.bound:
                        user_conn = tc
                        break
                except Exception:
                    continue

            if not user_conn or not user_conn.bound:
                return False, None, None, None, "Invalid corporate username/email or password."

            # Fetch user attributes under their own connection
            safe_id = escape_filter_chars(clean_id)
            safe_user = escape_filter_chars(clean_user)
            upn_cand = escape_filter_chars(f"{clean_user}@{ldap_domain}") if ldap_domain else safe_id
            search_filter = (
                f"(&(objectCategory=person)(objectClass=user)"
                f"(|(mail={safe_id})(userPrincipalName={safe_id})(userPrincipalName={upn_cand})"
                f"(sAMAccountName={safe_id})(sAMAccountName={safe_user})))"
            )
            user_conn.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['distinguishedName', 'sAMAccountName', 'userPrincipalName', 'displayName', 'mail', 'memberOf']
            )
            if user_conn.entries:
                user_entry = user_conn.entries[0]
                user_dn = str(user_entry.entry_dn if hasattr(user_entry, 'entry_dn') else user_entry.distinguishedName)
            user_conn.unbind()

        # Resolve display name & email/login
        display_name = clean_user
        resolved_username = clean_id.lower()
        user_groups = []

        if user_entry:
            if hasattr(user_entry, 'displayName') and user_entry.displayName:
                display_name = str(user_entry.displayName)
            if hasattr(user_entry, 'mail') and user_entry.mail:
                resolved_username = str(user_entry.mail).strip().lower()
            elif hasattr(user_entry, 'sAMAccountName') and user_entry.sAMAccountName:
                resolved_username = str(user_entry.sAMAccountName).strip().lower()
            if hasattr(user_entry, 'memberOf') and user_entry.memberOf:
                user_groups = [str(g).lower() for g in user_entry.memberOf]

        # Group Membership Check
        def is_member_of_group(target_group: str) -> bool:
            if not target_group:
                return False
            target_lower = target_group.lower()
            for g in user_groups:
                if target_lower == g or f"cn={target_lower}," in g:
                    return True
            # Nested group resolution via LDAP_MATCHING_RULE_IN_CHAIN
            if settings.LDAP_NESTED_GROUPS and user_dn and bind_user and bind_password:
                try:
                    s_conn = Connection(server, user=bind_user, password=bind_password, auto_bind=True)
                    safe_grp = escape_filter_chars(target_group)
                    grp_filter = f"(&(objectCategory=group)(|(cn={safe_grp})(distinguishedName={safe_grp})))"
                    s_conn.search(search_base=base_dn, search_filter=grp_filter, search_scope=SUBTREE, attributes=['distinguishedName'])
                    if s_conn.entries:
                        group_dn = escape_filter_chars(str(s_conn.entries[0].entry_dn if hasattr(s_conn.entries[0], 'entry_dn') else s_conn.entries[0].distinguishedName))
                        safe_user_dn = escape_filter_chars(user_dn)
                        nested_filter = f"(&(objectCategory=person)(objectClass=user)(distinguishedName={safe_user_dn})(memberOf:1.2.840.113556.1.4.1941:={group_dn}))"
                        s_conn.search(search_base=base_dn, search_filter=nested_filter, search_scope=SUBTREE, attributes=['distinguishedName'])
                        is_member = len(s_conn.entries) > 0
                        s_conn.unbind()
                        return is_member
                    s_conn.unbind()
                except Exception as e:
                    logger.warning(f"[LDAP] Nested group check error: {e}")
            return False

        if req_group and not is_member_of_group(req_group):
            return False, None, None, None, f"Access denied: User is not a member of required group «{req_group}»"

        # Role determination
        admin_users_set: Set[str] = set()
        if settings.LDAP_ADMIN_USERS:
            for u in settings.LDAP_ADMIN_USERS.split(","):
                u_str = u.strip().lower()
                if u_str:
                    admin_users_set.add(u_str)
                    if "@" in u_str:
                        admin_users_set.add(u_str.split("@")[0].strip())

        user_candidates = {clean_user.lower(), resolved_username.lower(), clean_id.lower()}
        if "@" in clean_id:
            user_candidates.add(clean_id.split("@")[0].lower())

        is_admin = bool(user_candidates & admin_users_set)
        if not is_admin and admin_group and is_member_of_group(admin_group):
            is_admin = True

        # If admin_group or admin_users is configured, non-admins are "viewer", otherwise default to "admin"
        if admin_group or admin_users_set:
            role = "admin" if is_admin else "viewer"
        else:
            role = "admin"

        return True, resolved_username, role, display_name, None

    except Exception as e:
        logger.exception(f"[LDAP ERROR] Connection error to DC {server_uri}: {e}")
        return False, None, None, None, f"Error connecting to Active Directory domain controller: {str(e)}"
