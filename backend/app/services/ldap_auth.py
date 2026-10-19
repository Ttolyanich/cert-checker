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
        return False, None, None, None, "Авторизация через LDAP/Active Directory отключена в настройках сервера."

    if not username or not password:
        return False, None, None, None, "Имя пользователя и пароль обязательны для заполнения."

    try:
        from ldap3 import Server, Connection, ALL, SUBTREE
        from ldap3.utils.conv import escape_filter_chars
    except ImportError:
        logger.error("Библиотека ldap3 не установлена в контейнере.")
        return False, None, None, None, "Библиотека ldap3 не установлена на сервере."

    server_uri = (settings.LDAP_SERVER or "").strip()
    base_dn = (settings.LDAP_BASE_DN or "").strip()
    ldap_domain = (settings.LDAP_DOMAIN or "").strip().lower()
    bind_user = (settings.LDAP_BIND_USER or "").strip()
    bind_password = settings.LDAP_BIND_PASSWORD or ""
    req_group = (settings.LDAP_REQUIRED_GROUP or "").strip()
    admin_group = (settings.LDAP_ADMIN_GROUP or "").strip()

    if not server_uri or not base_dn:
        logger.warning(f"[LDAP] Конфигурация неполная: LDAP_SERVER='{server_uri}', LDAP_BASE_DN='{base_dn}'")
        return False, None, None, None, "Настройки LDAP не заполнены (отсутствует LDAP_SERVER или LDAP_BASE_DN)."

    clean_id = username.strip()
    clean_user = clean_id
    if "\\" in clean_user:
        clean_user = clean_user.split("\\", 1)[1]
    if "@" in clean_user:
        clean_user = clean_user.split("@", 1)[0]

    domain_short = ldap_domain.split(".")[0].upper() if ldap_domain else ""

    try:
        use_ssl = server_uri.lower().startswith("ldaps://")
        server = Server(server_uri, use_ssl=use_ssl, get_info=ALL, connect_timeout=8)

        user_dn = None
        user_entry = None
        user_bound = False

        # Шаг 1: Если настроена сервисная учетная запись (Bind DN), ищем пользователя через нее
        if bind_user and bind_password:
            try:
                service_conn = Connection(server, user=bind_user, password=bind_password, auto_bind=True)
            except Exception as e:
                logger.error(f"[LDAP] Ошибка подключения сервисной учетной записи {bind_user}: {e}")
                return False, None, None, None, f"Ошибка привязки сервисной учетной записи LDAP: {e}"

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
                attributes=['distinguishedName', 'sAMAccountName', 'userPrincipalName', 'displayName', 'mail', 'memberOf', 'primaryGroupID']
            )

            if not service_conn.entries:
                service_conn.unbind()
                logger.warning(f"[LDAP] Пользователь '{clean_id}' не найден в Active Directory по фильтру {search_filter}")
                return False, None, None, None, "Пользователь не найден в каталоге Active Directory."

            user_entry = service_conn.entries[0]
            user_dn = str(user_entry.entry_dn if hasattr(user_entry, 'entry_dn') else user_entry.distinguishedName)
            user_sam = str(user_entry.sAMAccountName) if hasattr(user_entry, 'sAMAccountName') and user_entry.sAMAccountName else clean_user
            user_upn = str(user_entry.userPrincipalName) if hasattr(user_entry, 'userPrincipalName') and user_entry.userPrincipalName else ""
            service_conn.unbind()

            # Шаг 2: Проверка пароля пользователя перебором форматов UPN / DOMAIN\\user / sAMAccountName / user_dn
            verify_candidates = []
            if user_upn:
                verify_candidates.append(user_upn)
            if domain_short and user_sam:
                verify_candidates.append(f"{domain_short}\\{user_sam}")
            if ldap_domain and user_sam:
                verify_candidates.append(f"{user_sam}@{ldap_domain}")
            if user_sam:
                verify_candidates.append(user_sam)
            if user_dn:
                verify_candidates.append(user_dn)
            if "@" in clean_id:
                verify_candidates.append(clean_id)
            if "\\" in clean_id:
                verify_candidates.append(clean_id)

            for cand in dict.fromkeys([c for c in verify_candidates if c]):
                try:
                    tc = Connection(server, user=cand, password=password, auto_bind=True)
                    if tc.bound:
                        user_bound = True
                        tc.unbind()
                        break
                except Exception as e:
                    logger.debug(f"[LDAP] Попытка входа с кандидатом '{cand}' не удалась: {e}")
                    continue

            if not user_bound:
                logger.warning(f"[LDAP] Неверный пароль для доменного пользователя '{clean_id}'")
                return False, None, None, None, "Неверный пароль учетной записи Active Directory."

        # Шаг 1 (Fallback): Прямой Bind, если сервисная учетная запись не настроена
        else:
            direct_candidates = []
            if "@" in clean_id:
                direct_candidates.append(clean_id)
            if "\\" in clean_id:
                direct_candidates.append(clean_id)
            if domain_short:
                direct_candidates.append(f"{domain_short}\\{clean_user}")
            if ldap_domain:
                direct_candidates.append(f"{clean_user}@{ldap_domain}")
            direct_candidates.append(clean_user)

            user_conn = None
            for cand in dict.fromkeys([c for c in direct_candidates if c]):
                try:
                    tc = Connection(server, user=cand, password=password, auto_bind=True)
                    if tc.bound:
                        user_conn = tc
                        user_bound = True
                        break
                except Exception as e:
                    logger.debug(f"[LDAP] Direct bind candidate '{cand}' failed: {e}")
                    continue

            if not user_conn or not user_bound:
                return False, None, None, None, "Неверный логин/email или пароль учетной записи Active Directory."

            # Получаем атрибуты пользователя через его собственное соединение
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
                attributes=['distinguishedName', 'sAMAccountName', 'userPrincipalName', 'displayName', 'mail', 'memberOf', 'primaryGroupID']
            )
            if user_conn.entries:
                user_entry = user_conn.entries[0]
                user_dn = str(user_entry.entry_dn if hasattr(user_entry, 'entry_dn') else user_entry.distinguishedName)
            user_conn.unbind()

        # Шаг 3: Разрешение имени пользователя, почты и групп
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

        # Функция проверки членства в группе (с учетом Primary Group и вложенных групп)
        def is_member_of_group(target_group: str) -> bool:
            if not target_group:
                return False
            target_lower = target_group.lower().strip()

            # Active Directory: 'Domain Users' (RID 513) является Primary Group и не отображается в memberOf
            is_domain_users = target_lower in [
                "domain users",
                "пользователи домена",
                f"cn=domain users,cn=users,{base_dn.lower()}",
                f"cn=пользователи домена,cn=users,{base_dn.lower()}"
            ]
            if is_domain_users:
                if hasattr(user_entry, 'primaryGroupID') and str(user_entry.primaryGroupID) in ['513', '512']:
                    return True
                # В стандартном домене AD любой аутентифицированный пользователь входит в Domain Users
                return True

            for g in user_groups:
                if target_lower == g or f"cn={target_lower}," in g or g.startswith(f"cn={target_lower},"):
                    return True

            # Рекурсивный поиск во вложенных группах AD через LDAP_MATCHING_RULE_IN_CHAIN
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
                    logger.warning(f"[LDAP] Ошибка проверки вложенных групп: {e}")
            return False

        # Шаг 4: Проверка обязательной группы
        if req_group and not is_member_of_group(req_group):
            logger.warning(f"[LDAP] Пользователь '{resolved_username}' не состоит в обязательной группе '{req_group}'")
            return False, None, None, None, f"Доступ запрещен: учетная запись не состоит в группе «{req_group}»"

        # Шаг 5: Определение роли (admin или viewer)
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

        if admin_group or admin_users_set:
            role = "admin" if is_admin else "viewer"
        else:
            role = "admin"

        logger.info(f"[LDAP] Успешная авторизация пользователя '{resolved_username}' с ролью '{role}' (отображаемое имя: '{display_name}')")
        return True, resolved_username, role, display_name, None

    except Exception as e:
        logger.exception(f"[LDAP ERROR] Ошибка подключения к контроллеру домена {server_uri}: {e}")
        return False, None, None, None, f"Ошибка подключения к контроллеру домена Active Directory: {str(e)}"
