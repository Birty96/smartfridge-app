#!/usr/bin/env python3
"""
Generate a secure SECRET_KEY for Flask applications.

This script generates a cryptographically secure random key suitable
for use as a Flask SECRET_KEY environment variable.

Usage:
    python generate_secret_key.py

The generated key will be 64 characters long (32 bytes hex-encoded),
which provides 256 bits of entropy - more than sufficient for Flask applications.
"""

import secrets

def generate_secret_key():
    """Generate a cryptographically secure secret key."""
    return secrets.token_hex(32)

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print("Generated secure SECRET_KEY:")
    print(f"SECRET_KEY={secret_key}")
    print("\nCopy the line above to your .env file")
    print("WARNING: Keep this key secret and never commit it to version control!")