import socket
import ssl
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, List
from cryptography import x509
from cryptography.x509.oid import ExtensionOID

def clean_hostname_and_port(raw_host: str, default_port: int = 443) -> Tuple[str, int]:
    """
    Cleans raw hostname input: removes protocols (https://, http://),
    trailing paths/slashes, whitespace, and extracts explicit port if present.
    """
    if not raw_host:
        return "", default_port
    
    host = raw_host.strip().lower()
    
    # Strip protocols
    if "://" in host:
        host = host.split("://", 1)[1]
    
    # Strip paths, queries or fragments
    for delimiter in ("/", "?", "#"):
        if delimiter in host:
            host = host.split(delimiter, 1)[0]
            
    # Extract port if present (e.g., example.com:8443)
    port = default_port
    if ":" in host:
        parts = host.split(":")
        if len(parts) == 2 and parts[1].isdigit():
            host = parts[0]
            port = int(parts[1])
            
    return host.strip(), port


def check_ssl(hostname: str, port: int = 443, timeout: float = 6.0) -> Dict[str, Any]:
    """
    Checks the SSL certificate of a hostname and port with dual-stack IPv4/IPv6 support.
    Returns status, valid_from, valid_to, issuer, subject, sans, and error message.
    """
    clean_host, clean_port = clean_hostname_and_port(hostname, port)
    if not clean_host:
        return {
            "status": "error",
            "ssl_valid_from": None,
            "ssl_valid_to": None,
            "ssl_issuer": None,
            "last_error": "Hostname is empty or invalid",
            "last_checked": datetime.now(timezone.utc)
        }

    verified = True
    error_msg = None
    cert_bin = None

    # 1. Try verified SSL connection
    try:
        context = ssl.create_default_context()
        with socket.create_connection((clean_host, clean_port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=clean_host) as conn:
                cert_bin = conn.getpeercert(binary_form=True)
    except Exception as e:
        verified = False
        error_msg = str(e)

    # 2. If verified connection fails, try unverified connection to fetch certificate dates (e.g. self-signed or expired)
    if not verified:
        try:
            context = ssl._create_unverified_context()
            with socket.create_connection((clean_host, clean_port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=clean_host) as conn:
                    cert_bin = conn.getpeercert(binary_form=True)
        except Exception as e2:
            return {
                "status": "error",
                "ssl_valid_from": None,
                "ssl_valid_to": None,
                "ssl_issuer": None,
                "last_error": f"Connection failed: {error_msg}. (Unverified fallback: {e2})",
                "last_checked": datetime.now(timezone.utc)
            }

    # 3. Parse certificate data using cryptography
    try:
        cert = x509.load_der_x509_certificate(cert_bin)

        # cryptography >= 42.0.0 uses not_valid_before_utc / not_valid_after_utc
        try:
            valid_from = cert.not_valid_before_utc
            valid_to = cert.not_valid_after_utc
        except AttributeError:
            valid_from = cert.not_valid_before.replace(tzinfo=timezone.utc)
            valid_to = cert.not_valid_after.replace(tzinfo=timezone.utc)

        # Extract Common Name of the Issuer
        issuer = cert.issuer
        cn_attrs = issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        issuer_cn = cn_attrs[0].value if cn_attrs else "Unknown"

        now = datetime.now(timezone.utc)

        if now > valid_to:
            status = "expired"
            last_error = f"Certificate expired on {valid_to.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        elif not verified:
            status = "error"
            last_error = f"SSL Verification Failed: {error_msg}"
        else:
            status = "valid"
            last_error = None

        return {
            "status": status,
            "ssl_valid_from": valid_from,
            "ssl_valid_to": valid_to,
            "ssl_issuer": issuer_cn,
            "last_error": last_error,
            "last_checked": now
        }
    except Exception as e:
        return {
            "status": "error",
            "ssl_valid_from": None,
            "ssl_valid_to": None,
            "ssl_issuer": None,
            "last_error": f"Failed to parse certificate: {str(e)}",
            "last_checked": datetime.now(timezone.utc)
        }
