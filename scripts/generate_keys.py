#!/usr/bin/env python3
"""
Script to generate cryptographic keys for the Universal FastAPI Foundation.

This script generates:
1. A strong secret key for HS256 JWT signing
2. An RSA keypair for RS256 JWT signing
3. A Fernet key for field-level encryption
"""

import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_secret_key(length: int = 32) -> str:
    """Generate a random secret key for HS256 JWT signing."""
    return secrets.token_urlsafe(length)


def generate_rsa_keypair(private_key_path: str, public_key_path: str) -> None:
    """Generate an RSA keypair for RS256 JWT signing."""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Write private key to file
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Write public key to file
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
    
    # Set restrictive permissions on private key
    os.chmod(private_key_path, 0o600)


def generate_fernet_key() -> str:
    """Generate a Fernet key for field-level encryption."""
    return Fernet.generate_key().decode()


def main():
    """Main function to generate all keys."""
    print("Generating cryptographic keys for Universal FastAPI Foundation...")
    
    # Create keys directory if it doesn't exist
    keys_dir = Path("keys")
    keys_dir.mkdir(exist_ok=True)
    
    # Generate secret key for HS256
    secret_key = generate_secret_key()
    print(f"Generated SECRET_KEY: {secret_key}")
    
    # Generate RSA keypair for RS256
    private_key_path = keys_dir / "jwt_private_key.pem"
    public_key_path = keys_dir / "jwt_public_key.pem"
    generate_rsa_keypair(str(private_key_path), str(public_key_path))
    print(f"Generated RSA keypair:")
    print(f"  Private key: {private_key_path}")
    print(f"  Public key: {public_key_path}")
    
    # Generate Fernet key for encryption
    fernet_key = generate_fernet_key()
    print(f"Generated ENCRYPTION_KEY: {fernet_key}")
    
    # Write keys to .env file
    env_path = Path(".env")
    env_lines = []
    
    # Read existing .env if it exists
    if env_path.exists():
        with open(env_path, "r") as f:
            env_lines = f.readlines()
    
    # Update or add the key values
    updated_lines = []
    secret_key_set = False
    private_key_path_set = False
    public_key_path_set = False
    encryption_key_set = False
    
    for line in env_lines:
        if line.startswith("SECRET_KEY="):
            updated_lines.append(f"SECRET_KEY={secret_key}\n")
            secret_key_set = True
        elif line.startswith("JWT_PRIVATE_KEY_PATH="):
            updated_lines.append(f"JWT_PRIVATE_KEY_PATH={private_key_path}\n")
            private_key_path_set = True
        elif line.startswith("JWT_PUBLIC_KEY_PATH="):
            updated_lines.append(f"JWT_PUBLIC_KEY_PATH={public_key_path}\n")
            public_key_path_set = True
        elif line.startswith("ENCRYPTION_KEY="):
            updated_lines.append(f"ENCRYPTION_KEY={fernet_key}\n")
            encryption_key_set = True
        else:
            updated_lines.append(line)
    
    # Add missing keys if they weren't in the original file
    if not secret_key_set:
        updated_lines.append(f"SECRET_KEY={secret_key}\n")
    if not private_key_path_set:
        updated_lines.append(f"JWT_PRIVATE_KEY_PATH={private_key_path}\n")
    if not public_key_path_set:
        updated_lines.append(f"JWT_PUBLIC_KEY_PATH={public_key_path}\n")
    if not encryption_key_set:
        updated_lines.append(f"ENCRYPTION_KEY={fernet_key}\n")
    
    # Write back to .env file
    with open(env_path, "w") as f:
        f.writelines(updated_lines)
    
    print(f"\nKeys have been generated and added to {env_path}")
    print("\nNext steps:")
    print("1. Review the generated keys in the .env file")
    print("2. For production, consider storing keys in a secure secret manager")
    print("3. To use RS256, set JWT_ALGORITHM=RS256 in your .env file")


if __name__ == "__main__":
    main()
