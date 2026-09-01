"""RSA Key Management for RS256 JWT signing."""
import base64
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class RSAKeyManager:
    """Manages RSA key pair generation, loading, and JWKS generation."""

    def __init__(
        self,
        private_key_path: str,
        public_key_path: str,
        key_size: int = 2048,
    ):
        self.private_key_path = Path(private_key_path)
        self.public_key_path = Path(public_key_path)
        self.key_size = key_size
        self._private_key = None
        self._public_key = None

    def generate_keys(self) -> tuple[bytes, bytes]:
        """Generate new RSA key pair and save to files."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend(),
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Ensure directory exists
        self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
        self.public_key_path.parent.mkdir(parents=True, exist_ok=True)

        # Save keys
        self.private_key_path.write_bytes(private_pem)
        self.public_key_path.write_bytes(public_pem)

        # Set restrictive permissions (Unix-like systems)
        try:
            os.chmod(self.private_key_path, 0o600)
            os.chmod(self.public_key_path, 0o644)
        except OSError:
            pass  # Windows doesn't support chmod

        self._private_key = private_key
        self._public_key = public_key

        return private_pem, public_pem

    def load_keys(self) -> bool:
        """Load existing keys from files."""
        try:
            if not self.private_key_path.exists() or not self.public_key_path.exists():
                return False

            private_pem = self.private_key_path.read_bytes()
            public_pem = self.public_key_path.read_bytes()

            self._private_key = serialization.load_pem_private_key(
                private_pem, password=None, backend=default_backend()
            )
            self._public_key = serialization.load_pem_public_key(
                public_pem, backend=default_backend()
            )
            return True
        except Exception:
            return False

    def ensure_keys(self) -> tuple[bytes, bytes]:
        """Ensure keys exist, generating if necessary."""
        if not self.load_keys():
            return self.generate_keys()
        return (
            self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            self._public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ),
        )

    @property
    def private_key(self):
        if self._private_key is None:
            self.ensure_keys()
        return self._private_key

    @property
    def public_key(self):
        if self._public_key is None:
            self.ensure_keys()
        return self._public_key

    def get_jwks(self) -> dict:
        """Generate JWKS (JSON Web Key Set) for public key discovery."""
        public_numbers = self.public_key.public_numbers()

        # Base64url encode without padding
        def b64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).decode().rstrip("=")

        n = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
        e = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": "medverify-rsa-2024",
                    "n": b64url_encode(n),
                    "e": b64url_encode(e),
                }
            ]
        }

    def get_private_key_pem(self) -> str:
        """Get private key as PEM string."""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    def get_public_key_pem(self) -> str:
        """Get public key as PEM string."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()


# Singleton instance
_key_manager: Optional[RSAKeyManager] = None


def get_key_manager(
    private_key_path: Optional[str] = None,
    public_key_path: Optional[str] = None,
    key_size: Optional[int] = None,
) -> RSAKeyManager:
    """Get or create the global RSA key manager."""
    global _key_manager
    if _key_manager is None:
        from .config import RSA_KEY_SIZE, RSA_PRIVATE_KEY_PATH, RSA_PUBLIC_KEY_PATH
        _key_manager = RSAKeyManager(
            private_key_path or RSA_PRIVATE_KEY_PATH,
            public_key_path or RSA_PUBLIC_KEY_PATH,
            key_size or RSA_KEY_SIZE,
        )
        _key_manager.ensure_keys()
    return _key_manager
