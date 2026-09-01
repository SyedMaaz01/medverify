from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANUFACTURER = "manufacturer"
    AUDITOR = "auditor"
    API_CLIENT = "api_client"


class Permission(str, Enum):
    MANAGE_USERS = "manage_users"
    MANAGE_MANUFACTURERS = "manage_manufacturers"
    MANAGE_API_KEYS = "manage_api_keys"
    REGISTER_BATCHES = "register_batches"
    VERIFY_CODES = "verify_codes"
    VIEW_OWN_BATCHES = "view_own_batches"
    VIEW_ALL_BATCHES = "view_all_batches"
    GENERATE_QR_CODES = "generate_qr_codes"
    VIEW_OWN_SCANS = "view_own_scans"
    VIEW_ALL_SCANS = "view_all_scans"
    MANAGE_FLAGS = "manage_flags"
    VIEW_FLAGS = "view_flags"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_AUDIT_LOGS = "view_audit_logs"


class ManufacturerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    drap_license_no: str = Field(..., min_length=1)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class ManufacturerResponse(BaseModel):
    id: UUID
    name: str
    drap_license_no: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    created_at: datetime
    is_active: bool
    is_verified: bool
    email_verified: bool
    role: UserRole
    totp_enabled: bool
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class ManufacturerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class ManufacturerProfile(BaseModel):
    """Full profile including sensitive fields for self."""
    id: UUID
    name: str
    drap_license_no: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    created_at: datetime
    is_active: bool
    is_verified: bool
    email_verified: bool
    role: UserRole
    totp_enabled: bool
    backup_codes_remaining: int
    last_login: Optional[datetime]
    failed_login_attempts: int
    locked_until: Optional[datetime]

    class Config:
        from_attributes = True


class BatchCreate(BaseModel):
    manufacturer_id: UUID
    drug_name: str = Field(..., min_length=1)
    manufacturer_name: str = Field(..., min_length=1)
    draper_reg_no: str = Field(..., min_length=1)
    batch_number: str = Field(..., min_length=1, max_length=50)
    manufacture_date: date
    expiry_date: date


class BatchResponse(BaseModel):
    id: UUID
    manufacturer_id: UUID
    drug_name: str
    manufacturer_name: str
    draper_reg_no: str
    batch_number: str
    manufacture_date: date
    expiry_date: date
    signed_code: str
    status: str
    recalled_at: Optional[datetime]
    recall_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BatchUpdate(BaseModel):
    drug_name: Optional[str] = Field(None, min_length=1)
    manufacturer_name: Optional[str] = Field(None, min_length=1)
    draper_reg_no: Optional[str] = Field(None, min_length=1)
    batch_number: Optional[str] = Field(None, min_length=1, max_length=50)
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None


class ScanCreate(BaseModel):
    signed_code_scanned: str = Field(..., min_length=1)


class ScanResponse(BaseModel):
    id: UUID
    batch_id: Optional[UUID]
    signed_code_scanned: str
    timestamp: datetime
    ip_address: Optional[str]
    approx_location: Optional[str]
    result: str
    risk_score: float

    class Config:
        from_attributes = True


class SuspiciousActivity(BaseModel):
    code: str
    scan_count: int
    window_hours: int
    locations: list[str]

    class Config:
        from_attributes = True


class FlagResponse(BaseModel):
    id: UUID
    batch_id: UUID
    reason: str
    severity: str
    created_at: datetime
    resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    drap_license_no: str = Field(..., min_length=1)
    password: Optional[str] = None
    totp_token: Optional[str] = None
    backup_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    manufacturer: ManufacturerResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class QRCodeResponse(BaseModel):
    qr_code_url: str
    signed_code: str
    verify_url: str


class VerificationResponse(BaseModel):
    status: str
    detail: str
    drug_name: Optional[str] = None
    batch_number: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    risk_score: Optional[float] = None


class RecallBatchRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class FlagCreate(BaseModel):
    batch_id: UUID
    reason: str = Field(..., min_length=1)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class FlagResolveRequest(BaseModel):
    resolved_by: UUID


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1)
    scopes: list[str] = Field(default=["read"])
    rate_limit_tier: str = Field(default="free", pattern="^(free|pro|enterprise)$")
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Only returned on creation
    scopes: list[str]
    rate_limit_tier: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class WebhookCreate(BaseModel):
    url: str = Field(..., pattern="^https://.*")
    events: list[str] = Field(..., min_items=1)
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    id: UUID
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    items: list[BaseModel]
    total: int
    page: int
    page_size: int
    total_pages: int


# 2FA Schemas
class TotpSetupRequest(BaseModel):
    pass


class TotpSetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: list[str]


class TotpVerifyRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)


class TotpDisableRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6)


class BackupCodesResponse(BaseModel):
    codes: list[str]


# Email Verification
class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# JWKS
class JWKResponse(BaseModel):
    keys: list[dict]
