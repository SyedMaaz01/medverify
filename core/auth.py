"""Authentication and Authorization module with RS256, 2FA, RBAC, and API Keys."""
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import pyotp
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import APIKey, Manufacturer, Permission, UserRole
from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_MINUTES,
)
from .database import get_async_db
from .keys import get_key_manager

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_private_key() -> str:
    """Get RSA private key for signing."""
    return get_key_manager().get_private_key_pem()


def get_public_key() -> str:
    """Get RSA public key for verification."""
    return get_key_manager().get_public_key_pem()


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    """Create JWT access token with RS256."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": token_type, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, get_private_key(), algorithm=ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "refresh", "iat": datetime.utcnow()})
    return jwt.encode(to_encode, get_private_key(), algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[dict[str, Any]]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, get_public_key(), algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[UUID]:
    """Verify access token and return user ID."""
    payload = verify_token(token, "access")
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        return UUID(user_id)
    except ValueError:
        return None


def verify_refresh_token(token: str) -> Optional[UUID]:
    """Verify refresh token and return user ID."""
    payload = verify_token(token, "refresh")
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        return UUID(user_id)
    except ValueError:
        return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# 2FA / TOTP Functions
def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "MedVerify") -> str:
    """Get TOTP URI for QR code generation."""
    return pyotp.totp.TOTP(secret).provisioning_uri(email, issuer_name=issuer)


def verify_totp(secret: str, token: str, valid_window: int = 1) -> bool:
    """Verify TOTP token with a valid window for clock drift."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=valid_window)


def generate_backup_codes(count: int = 10, length: int = 8) -> list[str]:
    """Generate backup codes for 2FA recovery."""
    return [secrets.token_hex(length // 2).upper() for _ in range(count)]


def hash_backup_code(code: str) -> str:
    """Hash a backup code for storage."""
    return pwd_context.hash(code)


def verify_backup_code(plain_code: str, hashed_code: str) -> bool:
    """Verify a backup code."""
    return pwd_context.verify(plain_code.upper(), hashed_code)


# Permission System
ROLE_PERMISSIONS: dict[UserRole, list[Permission]] = {
    UserRole.SUPER_ADMIN: list(Permission),  # All permissions
    UserRole.ADMIN: [
        Permission.MANAGE_USERS,
        Permission.MANAGE_MANUFACTURERS,
        Permission.VIEW_ALL_BATCHES,
        Permission.VIEW_ALL_SCANS,
        Permission.MANAGE_FLAGS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_API_KEYS,
        Permission.VIEW_AUDIT_LOGS,
    ],
    UserRole.MANUFACTURER: [
        Permission.REGISTER_BATCHES,
        Permission.VIEW_OWN_BATCHES,
        Permission.VIEW_OWN_SCANS,
        Permission.GENERATE_QR_CODES,
    ],
    UserRole.AUDITOR: [
        Permission.VIEW_ALL_BATCHES,
        Permission.VIEW_ALL_SCANS,
        Permission.VIEW_FLAGS,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_AUDIT_LOGS,
    ],
    UserRole.API_CLIENT: [
        Permission.REGISTER_BATCHES,
        Permission.VERIFY_CODES,
        Permission.VIEW_OWN_BATCHES,
    ],
}


def get_permissions_for_role(role: UserRole) -> list[Permission]:
    """Get permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user_role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(user_role, [])


# API Key Functions
def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and its hash."""
    # Format: mk_live_<random> or mk_test_<random>
    prefix = "mk_live_"  # In production, determine from environment
    raw_key = prefix + secrets.token_urlsafe(32)
    key_hash = hash_password(raw_key)
    return raw_key, key_hash


async def get_current_manufacturer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db),
) -> Manufacturer:
    """Get current authenticated manufacturer from JWT."""
    manufacturer_id = verify_access_token(credentials.credentials)
    if manufacturer_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.id == manufacturer_id)
    )
    manufacturer = result.scalar_one_or_none()
    if manufacturer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Manufacturer not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not manufacturer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return manufacturer


async def get_current_user_with_api_key(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_async_db),
) -> Manufacturer:
    """Authenticate via API key (for server-to-server)."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    # Find all active API keys and verify
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    api_keys = result.scalars().all()

    for key_obj in api_keys:
        if verify_password(api_key, key_obj.key_hash):
            # Check expiration
            if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired",
                )

            # Update last used
            key_obj.last_used_at = datetime.utcnow()
            await db.commit()

            # Get manufacturer
            result = await db.execute(
                select(Manufacturer).where(Manufacturer.id == key_obj.user_id)
            )
            manufacturer = result.scalar_one_or_none()
            if manufacturer and manufacturer.is_active:
                return manufacturer

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_async_db),
) -> Manufacturer:
    """Get current user from either JWT or API key."""
    if api_key:
        return await get_current_user_with_api_key(request, api_key, db)
    if credentials:
        return await get_current_manufacturer(credentials, db)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


def require_permission(permission: Permission):
    """Dependency to require a specific permission."""
    async def permission_checker(
        current_user: Manufacturer = Depends(get_current_user),
    ) -> Manufacturer:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission.value}",
            )
        return current_user
    return permission_checker


def require_role(*roles: UserRole):
    """Dependency to require one of the specified roles."""
    async def role_checker(
        current_user: Manufacturer = Depends(get_current_user),
    ) -> Manufacturer:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: one of {[r.value for r in roles]}",
            )
        return current_user
    return role_checker


async def get_admin_user(
    current_user: Manufacturer = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
) -> Manufacturer:
    """Dependency for admin-only endpoints."""
    return current_user


async def get_super_admin_user(
    current_user: Manufacturer = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> Manufacturer:
    """Dependency for super admin only endpoints."""
    return current_user


# Token pair creation
async def create_token_pair(
    manufacturer: Manufacturer,
    device_info: Optional[str] = None,
) -> dict[str, str]:
    """Create access and refresh token pair."""
    token_data = {
        "sub": str(manufacturer.id),
        "email": manufacturer.contact_email,
        "role": manufacturer.role.value,
        "permissions": [p.value for p in get_permissions_for_role(manufacturer.role)],
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
