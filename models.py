import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANUFACTURER = "manufacturer"
    AUDITOR = "auditor"
    API_CLIENT = "api_client"


class Permission(str, enum.Enum):
    # User management
    MANAGE_USERS = "manage_users"
    MANAGE_MANUFACTURERS = "manage_manufacturers"
    MANAGE_API_KEYS = "manage_api_keys"

    # Batch operations
    REGISTER_BATCHES = "register_batches"
    VERIFY_CODES = "verify_codes"
    VIEW_OWN_BATCHES = "view_own_batches"
    VIEW_ALL_BATCHES = "view_all_batches"
    GENERATE_QR_CODES = "generate_qr_codes"

    # Scans
    VIEW_OWN_SCANS = "view_own_scans"
    VIEW_ALL_SCANS = "view_all_scans"

    # Flags & Analytics
    MANAGE_FLAGS = "manage_flags"
    VIEW_FLAGS = "view_flags"
    VIEW_ANALYTICS = "view_analytics"

    # Audit
    VIEW_AUDIT_LOGS = "view_audit_logs"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.utcnow()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)


class Manufacturer(Base, TimestampMixin):
    __tablename__ = "manufacturers"
    __table_args__ = (
        Index("ix_manufacturers_drap_license_no", "drap_license_no", unique=True),
        Index("ix_manufacturers_email", "contact_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    drap_license_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.MANUFACTURER,
        nullable=False,
    )
    totp_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of hashed codes
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    batches: Mapped[list["Batch"]] = relationship(
        "Batch", back_populates="manufacturer", lazy="selectin"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )


class Batch(Base, TimestampMixin):
    __tablename__ = "batches"
    __table_args__ = (
        Index("ix_batches_signed_code", "signed_code", unique=True),
        Index("ix_batches_batch_number", "batch_number", unique=True),
        Index("ix_batches_manufacturer_id", "manufacturer_id"),
        Index("ix_batches_expiry_date", "expiry_date"),
        Index("ix_batches_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manufacturers.id"), nullable=False
    )
    drug_name: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacturer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    draper_reg_no: Mapped[str] = mapped_column(String(80), nullable=False, default="STUB")
    batch_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    manufacture_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    signed_code: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    recalled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    recall_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    manufacturer: Mapped["Manufacturer"] = relationship(
        "Manufacturer", back_populates="batches", lazy="selectin"
    )
    scans: Mapped[list["Scan"]] = relationship(
        "Scan", back_populates="batch", cascade="all, delete-orphan", lazy="selectin"
    )
    flags: Mapped[list["Flag"]] = relationship(
        "Flag", back_populates="batch", cascade="all, delete-orphan", lazy="selectin"
    )


class Scan(Base, TimestampMixin):
    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_code_timestamp", "signed_code_scanned", "timestamp"),
        Index("ix_scans_ip_timestamp", "ip_address", "timestamp"),
        Index("ix_scans_result", "result"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("batches.id"), nullable=True, index=True
    )
    signed_code_scanned: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, server_default=func.now()
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    approx_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    risk_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    risk_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    batch: Mapped[Optional["Batch"]] = relationship(
        "Batch", back_populates="scans", lazy="selectin"
    )


class Flag(Base, TimestampMixin):
    __tablename__ = "flags"
    __table_args__ = (
        Index("ix_flags_resolved", "resolved"),
        Index("ix_flags_created_at", "created_at"),
        Index("ix_flags_severity", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batches.id"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="flags", lazy="selectin")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, server_default=func.now()
    )


class APIKey(Base, TimestampMixin):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_hash", "key_hash", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("manufacturers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    scopes: Mapped[str] = mapped_column(String(500), nullable=False)
    rate_limit_tier: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["Manufacturer"] = relationship(
        "Manufacturer", back_populates="api_keys", lazy="selectin"
    )
