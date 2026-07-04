import socket
import ssl
from datetime import datetime, timezone
from cryptography import x509

def check_ssl(hostname: str, port: int = 443) -> dict:
    """
    Checks the SSL certificate of a hostname and port.
    Returns a dictionary with status, valid_from, valid_to, issuer, and error message.
    """
    verified = True
    error_msg = None
    cert_bin = None
    
    # 1. Try verified connection
    try:
        context = ssl.create_default_context()
        # Avoid hanging on slow connections
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        conn = context.wrap_socket(sock, server_hostname=hostname)
        conn.connect((hostname, port))
        cert_bin = conn.getpeercert(binary_form=True)
        conn.close()
    except Exception as e:
        verified = False
        error_msg = str(e)
        
    # 2. If verified connection fails, try unverified connection to fetch certificate dates
    if not verified:
        try:
            context = ssl._create_unverified_context()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            
            conn = context.wrap_socket(sock, server_hostname=hostname)
            conn.connect((hostname, port))
            cert_bin = conn.getpeercert(binary_form=True)
            conn.close()
        except Exception as e2:
            # Connection failed completely (DNS, network, port closed)
            return {
                "status": "error",
                "ssl_valid_from": None,
                "ssl_valid_to": None,
                "ssl_issuer": None,
                "last_error": f"Connection failed: {error_msg}. Unverified retry failed: {str(e2)}",
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
            # Fallback for older cryptography versions
            valid_from = cert.not_valid_before.replace(tzinfo=timezone.utc)
            valid_to = cert.not_valid_after.replace(tzinfo=timezone.utc)
            
        # Extract Common Name of the Issuer
        issuer = cert.issuer
        issuer_cn = "Unknown"
        for attribute in issuer:
            if attribute.oid._name == "commonName":
                issuer_cn = attribute.value
                break
                
        now = datetime.now(timezone.utc)
        
        if now > valid_to:
            status = "expired"
            last_error = "Certificate has expired"
        elif not verified:
            # The certificate is not expired, but verification failed (e.g. self-signed, hostname mismatch)
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
