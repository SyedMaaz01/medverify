"""Authentication API endpoints."""
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import (
    UserRole,
    create_token_pair,
    generate_api_key,
    generate_backup_codes,
    generate_totp_secret,
    get_admin_user,
    get_current_user,
    get_totp_uri,
    hash_backup_code,
    hash_password,
    verify_backup_code,
    verify_password,
    verify_refresh_token,
    verify_totp,
)
from ..core.config import ENABLE_2FA, ENABLE_EMAIL_VERIFICATION, ENABLE_PASSWORD_RESET
from ..core.database import get_async_db
from ..core.email import get_email_service
from ..core.keys import get_key_manager
from ..models import APIKey, AuditLog, Manufacturer
from ..schemas import (
    APIKeyCreate,
    APIKeyResponse,
    BackupCodesResponse,
    EmailVerificationConfirm,
    EmailVerificationRequest,
    JWKResponse,
    LoginRequest,
    ManufacturerCreate,
    ManufacturerProfile,
    ManufacturerResponse,
    ManufacturerUpdate,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    TotpDisableRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()


async def log_audit(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    request: Optional[Request] = None,
    metadata: Optional[str] = None,
):
    """Log audit trail."""
    client_ip = None
    user_agent = None
    if request:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        user_agent = request.headers.get("User-Agent")

    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=client_ip,
        user_agent=user_agent,
        extra_data=metadata,
    )
    db.add(audit)


# ============================================================================
# REGISTRATION & LOGIN
# ============================================================================

@router.post("/register", response_model=ManufacturerResponse, status_code=201)
async def register_manufacturer(
    payload: ManufacturerCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """Register a new manufacturer account."""
    # Check for duplicate DRAP license number
    existing = await db.execute(
        select(Manufacturer).where(Manufacturer.drap_license_no == payload.drap_license_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Manufacturer with this DRAP license number already exists"
        )

    # Check for duplicate email
    if payload.contact_email:
        existing = await db.execute(
            select(Manufacturer).where(Manufacturer.contact_email == payload.contact_email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail="Email already registered"
            )

    # Hash password if provided
    password_hash = hash_password(payload.password) if payload.password else None

    now = datetime.now(UTC)
    manufacturer = Manufacturer(
        name=payload.name,
        drap_license_no=payload.drap_license_no,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        password_hash=password_hash,
        role=UserRole.MANUFACTURER,
        is_active=True,
        is_verified=False,
        email_verified=not ENABLE_EMAIL_VERIFICATION,  # Auto-verify if disabled
        created_at=now,
        updated_at=now,
    )
    db.add(manufacturer)
    await db.commit()
    await db.refresh(manufacturer)

    # Send verification email if enabled
    if ENABLE_EMAIL_VERIFICATION and payload.contact_email:
        from secrets import token_urlsafe
        verification_token = token_urlsafe(32)
        manufacturer.email_verification_token = hash_password(verification_token)
        manufacturer.email_verification_expires = datetime.now(UTC) + timedelta(hours=24)
        await db.commit()

        email_service = get_email_service()
        background_tasks.add_task(
            email_service.send_verification_email,
            payload.contact_email,
            verification_token,
            payload.name,
        )

    # Audit log
    await log_audit(db, "manufacturer_registered", "manufacturer", manufacturer.id, None, request)
    await db.commit()

    return ManufacturerResponse(
        id=manufacturer.id,
        name=manufacturer.name,
        drap_license_no=manufacturer.drap_license_no,
        contact_email=manufacturer.contact_email,
        contact_phone=manufacturer.contact_phone,
        created_at=manufacturer.created_at,
        is_active=manufacturer.is_active,
        is_verified=manufacturer.is_verified,
        email_verified=manufacturer.email_verified,
        role=manufacturer.role,
        totp_enabled=manufacturer.totp_enabled,
        last_login=manufacturer.last_login,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """Login with DRAP license number and password + optional 2FA."""
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.drap_license_no == payload.drap_license_no)
    )
    manufacturer = result.scalar_one_or_none()
    if not manufacturer:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check account lock
    if manufacturer.locked_until and manufacturer.locked_until > datetime.now(UTC):
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked due to failed login attempts"
        )

    # Verify password
    if not manufacturer.password_hash or not verify_password(payload.password, manufacturer.password_hash):
        # Increment failed attempts
        manufacturer.failed_login_attempts += 1
        if manufacturer.failed_login_attempts >= 5:
            manufacturer.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check 2FA
    if manufacturer.totp_enabled and ENABLE_2FA:
        if not payload.totp_token and not payload.backup_code:
            # Need 2FA token
            raise HTTPException(
                status_code=400,
                detail="2FA token required",
                headers={"X-Requires-2FA": "true"},
            )

        verified = False
        if payload.totp_token:
            verified = verify_totp(manufacturer.totp_secret, payload.totp_token)
        elif payload.backup_code:
            # Check backup codes
            if manufacturer.backup_codes:
                backup_codes = json.loads(manufacturer.backup_codes)
                for i, hashed_code in enumerate(backup_codes):
                    if verify_backup_code(payload.backup_code, hashed_code):
                        # Remove used backup code
                        backup_codes.pop(i)
                        manufacturer.backup_codes = json.dumps(backup_codes)
                        verified = True
                        break

        if not verified:
            raise HTTPException(status_code=401, detail="Invalid 2FA token")

    # Reset failed attempts on successful login
    manufacturer.failed_login_attempts = 0
    manufacturer.locked_until = None
    manufacturer.last_login = datetime.now(UTC)
    await db.commit()

    # Create token pair
    tokens = await create_token_pair(manufacturer)

    # Audit log
    await log_audit(db, "login", "manufacturer", manufacturer.id, manufacturer.id, request)
    await db.commit()

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        manufacturer=ManufacturerResponse(
            id=manufacturer.id,
            name=manufacturer.name,
            drap_license_no=manufacturer.drap_license_no,
            contact_email=manufacturer.contact_email,
            contact_phone=manufacturer.contact_phone,
            created_at=manufacturer.created_at,
            is_active=manufacturer.is_active,
            is_verified=manufacturer.is_verified,
            email_verified=manufacturer.email_verified,
            role=manufacturer.role,
            totp_enabled=manufacturer.totp_enabled,
            last_login=manufacturer.last_login,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """Refresh access token using refresh token."""
    manufacturer_id = verify_refresh_token(payload.refresh_token)
    if manufacturer_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(Manufacturer).where(Manufacturer.id == manufacturer_id)
    )
    manufacturer = result.scalar_one_or_none()
    if not manufacturer or not manufacturer.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    tokens = await create_token_pair(manufacturer)

    # Audit log
    await log_audit(db, "token_refresh", "manufacturer", manufacturer.id, manufacturer.id, request)
    await db.commit()

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        manufacturer=ManufacturerResponse(
            id=manufacturer.id,
            name=manufacturer.name,
            drap_license_no=manufacturer.drap_license_no,
            contact_email=manufacturer.contact_email,
            contact_phone=manufacturer.contact_phone,
            created_at=manufacturer.created_at,
            is_active=manufacturer.is_active,
            is_verified=manufacturer.is_verified,
            email_verified=manufacturer.email_verified,
            role=manufacturer.role,
            totp_enabled=manufacturer.totp_enabled,
            last_login=manufacturer.last_login,
        ),
    )


@router.post("/logout")
async def logout(
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Logout (client should discard tokens)."""
    await log_audit(
        db, "logout", "manufacturer", current_user.id, current_user.id
    )
    await db.commit()
    return {"message": "Logged out successfully"}


# ============================================================================
# PROFILE & PASSWORD MANAGEMENT
# ============================================================================

@router.get("/me", response_model=ManufacturerProfile)
async def get_profile(
    current_user: Manufacturer = Depends(get_current_user),
):
    """Get current user's full profile."""
    backup_codes_count = 0
    if current_user.backup_codes:
        try:
            backup_codes_count = len(json.loads(current_user.backup_codes))
        except Exception:
            pass

    return ManufacturerProfile(
        id=current_user.id,
        name=current_user.name,
        drap_license_no=current_user.drap_license_no,
        contact_email=current_user.contact_email,
        contact_phone=current_user.contact_phone,
        created_at=current_user.created_at,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        email_verified=current_user.email_verified,
        role=current_user.role,
        totp_enabled=current_user.totp_enabled,
        backup_codes_remaining=backup_codes_count,
        last_login=current_user.last_login,
        failed_login_attempts=current_user.failed_login_attempts,
        locked_until=current_user.locked_until,
    )


@router.put("/me", response_model=ManufacturerProfile)
async def update_profile(
    payload: ManufacturerUpdate,
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update current user's profile."""
    if payload.name is not None:
        current_user.name = payload.name
    if payload.contact_email is not None:
        current_user.contact_email = payload.contact_email
        current_user.email_verified = False
        # Send new verification email
        if ENABLE_EMAIL_VERIFICATION:
            verification_token = secrets.token_urlsafe(32)
            current_user.email_verification_token = hash_password(verification_token)
            current_user.email_verification_expires = datetime.now(UTC) + timedelta(hours=24)
            email_service = get_email_service()
            # In background
            email_service.send_verification_email(
                payload.contact_email, verification_token, current_user.name
            )
    if payload.contact_phone is not None:
        current_user.contact_phone = payload.contact_phone

    await db.commit()
    await db.refresh(current_user)
    return await get_profile(current_user)


@router.put("/me/password")
async def change_password(
    payload: PasswordChangeRequest,
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Change password."""
    if not current_user.password_hash or not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================

@router.post("/verify-email")
async def request_email_verification(
    payload: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """Request email verification link."""
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.contact_email == payload.email)
    )
    manufacturer = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if manufacturer and not manufacturer.email_verified and ENABLE_EMAIL_VERIFICATION:
        verification_token = secrets.token_urlsafe(32)
        manufacturer.email_verification_token = hash_password(verification_token)
        manufacturer.email_verification_expires = datetime.now(UTC) + timedelta(hours=24)
        await db.commit()

        email_service = get_email_service()
        background_tasks.add_task(
            email_service.send_verification_email,
            manufacturer.contact_email,
            verification_token,
            manufacturer.name,
        )

    return {"message": "If the email exists, a verification link has been sent"}


@router.post("/verify-email/confirm")
async def confirm_email_verification(
    payload: EmailVerificationConfirm,
    db: AsyncSession = Depends(get_async_db),
):
    """Confirm email verification token."""
    result = await db.execute(
        select(Manufacturer).where(
            Manufacturer.email_verification_expires > datetime.now(UTC)
        )
    )
    manufacturers = result.scalars().all()

    for manufacturer in manufacturers:
        if verify_password(payload.token, manufacturer.email_verification_token):
            manufacturer.email_verified = True
            manufacturer.email_verification_token = None
            manufacturer.email_verification_expires = None
            manufacturer.is_verified = True
            await db.commit()
            return {"message": "Email verified successfully"}

    raise HTTPException(status_code=400, detail="Invalid or expired verification token")


# ============================================================================
# PASSWORD RESET
# ============================================================================

@router.post("/password-reset")
async def request_password_reset(
    payload: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """Request password reset link."""
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.contact_email == payload.email)
    )
    manufacturer = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if manufacturer and ENABLE_PASSWORD_RESET:
        reset_token = secrets.token_urlsafe(32)
        manufacturer.password_reset_token = hash_password(reset_token)
        manufacturer.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
        await db.commit()

        email_service = get_email_service()
        background_tasks.add_task(
            email_service.send_password_reset_email,
            manufacturer.contact_email,
            reset_token,
            manufacturer.name,
        )

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_async_db),
):
    """Confirm password reset token."""
    result = await db.execute(
        select(Manufacturer).where(
            Manufacturer.password_reset_expires > datetime.now(UTC)
        )
    )
    manufacturers = result.scalars().all()

    for manufacturer in manufacturers:
        if verify_password(payload.token, manufacturer.password_reset_token):
            manufacturer.password_hash = hash_password(payload.password)
            manufacturer.password_reset_token = None
            manufacturer.password_reset_expires = None
            await db.commit()
            return {"message": "Password reset successfully"}

    raise HTTPException(status_code=400, detail="Invalid or expired reset token")


# ============================================================================
# 2FA / TOTP
# ============================================================================

@router.post("/2fa/setup", response_model=TotpSetupResponse)
async def setup_2fa(
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Setup 2FA - generate secret and QR code."""
    if not ENABLE_2FA:
        raise HTTPException(status_code=400, detail="2FA is disabled")

    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA already enabled")

    secret = generate_totp_secret()
    qr_uri = get_totp_uri(secret, current_user.contact_email or str(current_user.id))
    backup_codes = generate_backup_codes()
    hashed_backup_codes = [hash_backup_code(code) for code in backup_codes]

    # Store secret temporarily (not enabled until verified)
    current_user.totp_secret = secret
    current_user.backup_codes = json.dumps([hash_backup_code(c) for c in backup_codes])
    await db.commit()

    qr_uri = get_totp_uri(secret, current_user.contact_email or str(current_user.id))

    return TotpSetupResponse(
        secret=secret,
        qr_code_uri=qr_uri,
        backup_codes=backup_codes,
    )


@router.post("/2fa/verify")
async def verify_2fa_setup(
    payload: TotpVerifyRequest,
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Verify 2FA token to enable 2FA."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated")

    if not verify_totp(current_user.totp_secret, payload.token):
        raise HTTPException(status_code=400, detail="Invalid 2FA token")

    # Enable 2FA
    current_user.totp_enabled = True
    # Keep backup_codes (already hashed)
    await db.commit()

    # Send confirmation email
    if current_user.contact_email:
        email_service = get_email_service()
        backup_codes = []
        if current_user.backup_codes:
            # We can't decrypt, but we can tell user to save the ones they saw
            pass

    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    payload: TotpDisableRequest,
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Disable 2FA."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")

    if not verify_totp(current_user.totp_secret, payload.token):
        raise HTTPException(status_code=400, detail="Invalid 2FA token")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = None
    await db.commit()

    return {"message": "2FA disabled successfully"}


@router.get("/2fa/backup-codes", response_model=BackupCodesResponse)
async def get_backup_codes(
    current_user: Manufacturer = Depends(get_current_user),
):
    """Get backup codes (only available during setup)."""
    if not current_user.backup_codes:
        return BackupCodesResponse(codes=[])

    # We can't return the actual codes since they're hashed
    # This endpoint is mainly for the setup flow
    raise HTTPException(status_code=400, detail="Backup codes only available during setup")


@router.post("/2fa/regenerate-backup-codes", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Regenerate backup codes."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")

    backup_codes = generate_backup_codes()
    hashed_codes = [hash_backup_code(code) for code in backup_codes]
    current_user.backup_codes = json.dumps(hashed_codes)
    await db.commit()

    # Send email with new codes
    if current_user.contact_email:
        email_service = get_email_service()
        # In background
        email_service.send_2fa_setup_email(
            current_user.contact_email, current_user.name, backup_codes
        )

    return BackupCodesResponse(codes=backup_codes)


# ============================================================================
# API KEYS
# ============================================================================

@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_api_key(
    payload: APIKeyCreate,
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new API key."""
    raw_key, key_hash = generate_api_key()

    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=payload.expires_in_days)

    api_key = APIKey(
        user_id=current_user.id,
        name=payload.name,
        key_hash=key_hash,
        scopes=json.dumps(payload.scopes),
        rate_limit_tier=payload.rate_limit_tier,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only returned on creation
        scopes=json.loads(api_key.scopes),
        rate_limit_tier=api_key.rate_limit_tier,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        is_active=api_key.is_active,
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List user's API keys."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    api_keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key="",  # Never return key again
            scopes=json.loads(key.scopes),
            rate_limit_tier=key.rate_limit_tier,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            is_active=key.is_active,
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    current_user: Manufacturer = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revoke an API key."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.commit()
    return {"message": "API key revoked"}


# ============================================================================
# ADMIN USER MANAGEMENT
# ============================================================================

@router.get("/admin/users", response_model=list[ManufacturerResponse])
async def admin_list_users(
    page: int = 1,
    page_size: int = 50,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: Manufacturer = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all users (admin only)."""
    query = select(Manufacturer)
    if role:
        query = query.where(Manufacturer.role == role)
    if is_active is not None:
        query = query.where(Manufacturer.is_active == is_active)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Manufacturer.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = result.scalars().all()

    return [
        ManufacturerResponse(
            id=u.id,
            name=u.name,
            drap_license_no=u.drap_license_no,
            contact_email=u.contact_email,
            contact_phone=u.contact_phone,
            created_at=u.created_at,
            is_active=u.is_active,
            is_verified=u.is_verified,
            email_verified=u.email_verified,
            role=u.role,
            totp_enabled=u.totp_enabled,
            last_login=u.last_login,
        )
        for u in users
    ]


@router.put("/admin/users/{user_id}/role")
async def admin_update_user_role(
    user_id: UUID,
    role: UserRole,
    current_user: Manufacturer = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update user role (admin only)."""
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-demotion from super_admin
    if current_user.id == user_id and current_user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=400, detail="Cannot change own role")

    user.role = role
    await db.commit()
    return {"message": f"Role updated to {role.value}"}


@router.put("/admin/users/{user_id}/status")
async def admin_update_user_status(
    user_id: UUID,
    is_active: bool,
    current_user: Manufacturer = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Activate/deactivate user (admin only)."""
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot change own status")

    user.is_active = is_active
    await db.commit()
    return {"message": f"User {'activated' if is_active else 'deactivated'}"}


# ============================================================================
# JWKS ENDPOINT
# ============================================================================

@router.get("/.well-known/jwks.json", response_model=JWKResponse)
async def get_jwks():
    """Get JSON Web Key Set for token verification."""
    key_manager = get_key_manager()
    return JWKResponse(keys=key_manager.get_jwks()["keys"])
