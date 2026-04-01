"""
SSL/TLS Certificate Generation for SentryGround-Zero

Generates self-signed certificates for local development.
For production, use Let's Encrypt or your organization's CA.
"""

import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generate_self_signed_cert(
    hostname: str = "localhost",
    ip_addresses: list = None,
    output_dir: str = "./certs",
    days_valid: int = 365
) -> tuple[str, str]:
    """
    Generate self-signed SSL certificate for development.
    
    Returns:
        tuple: (cert_path, key_path)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "EU"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Space"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Mission Control"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SentryGround-Zero"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])
    
    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(subject)
    cert_builder = cert_builder.issuer_name(issuer)
    cert_builder = cert_builder.public_key(private_key.public_key())
    cert_builder = cert_builder.serial_number(x509.random_serial_number())
    cert_builder = cert_builder.not_valid_before(datetime.datetime.utcnow())
    cert_builder = cert_builder.not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
    )
    
    cert_builder = cert_builder.add_extension(
        x509.SubjectAlternativeName(
            [
                x509.DNSName(hostname),
                x509.DNSName("*.mission.local"),
                x509.DNSName("*.sentryground.local"),
            ] + ([x509.IPAddress(ip) for ip in ip_addresses] if ip_addresses else [])
        ),
        critical=False,
    )
    
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )
    
    cert = cert_builder.sign(private_key, hashes.SHA256(), default_backend())
    
    cert_path = os.path.join(output_dir, "server.crt")
    key_path = os.path.join(output_dir, "server.key")
    
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    os.chmod(key_path, 0o600)
    
    return cert_path, key_path


def generate_dhparam(output_dir: str = "./certs", key_size: int = 2048) -> str:
    """
    Generate Diffie-Hellman parameters for enhanced security.
    """
    from cryptography.hazmat.primitives.asymmetric import dh
    
    os.makedirs(output_dir, exist_ok=True)
    
    param_path = os.path.join(output_dir, "dhparam.pem")
    
    if not os.path.exists(param_path):
        from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
        
        parameters = dh.generate_parameters(generator=2, key_size=key_size, backend=default_backend())
        
        with open(param_path, "wb") as f:
            f.write(parameters.parameter_bytes(Encoding.PEM, NoEncryption()))
        
        os.chmod(param_path, 0o600)
    
    return param_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate SSL certificates")
    parser.add_argument("--hostname", default="localhost", help="Server hostname")
    parser.add_argument("--output", default="./certs", help="Output directory")
    parser.add_argument("--days", type=int, default=365, help="Certificate validity (days)")
    
    args = parser.parse_args()
    
    cert_path, key_path = generate_self_signed_cert(
        hostname=args.hostname,
        output_dir=args.output,
        days_valid=args.days
    )
    
    dh_path = generate_dhparam(args.output)
    
    print(f"✓ Certificate: {cert_path}")
    print(f"✓ Private Key: {key_path}")
    print(f"✓ DH Params: {dh_path}")
    print("\n⚠️  For production, replace with CA-signed certificates!")
