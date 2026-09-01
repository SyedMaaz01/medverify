import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import (
    create_access_token,
    create_refresh_token,
    get_admin_user,
    verify_password,
)
from ..core.database import get_async_db
from ..core.drap import DRAPClient, get_drap_client
from ..core.qr import generate_qr_code
from ..core.rate_limit import limiter
from ..core.security import parse_signed_code, sign_batch_code, verify_signature
from ..models import AuditLog, Batch, Manufacturer, Scan
from ..schemas import (
    BatchCreate,
    BatchResponse,
    LoginRequest,
    ManufacturerCreate,
    ManufacturerResponse,
    TokenResponse,
)

router = APIRouter(prefix="/api", tags=["medverify"])
security = HTTPBearer()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


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
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
        metadata=metadata,
    )
    db.add(audit)


@router.post("/register", response_model=BatchResponse, status_code=201)
async def register_batch(
    payload: BatchCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    drap_client: DRAPClient = Depends(get_drap_client),
):
    # Validate manufacturer exists
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.id == payload.manufacturer_id)
    )
    manufacturer = result.scalar_one_or_none()
    if not manufacturer:
        raise HTTPException(status_code=400, detail="Manufacturer not found")

    # DRAP lookup
    draper_result = drap_client.lookup(payload.draper_reg_no)
    if not draper_result or draper_result.status != "active":
        raise HTTPException(
            status_code=400,
            detail="DRAP registration not found or inactive",
        )

    # Generate signed code
    batch_id = uuid.uuid4()
    signed_code = sign_batch_code(
        batch_id,
        payload.batch_number,
        payload.drug_name,
        payload.expiry_date,
    )

    # Check for duplicate signed_code
    existing = await db.execute(
        select(Batch).where(Batch.signed_code == signed_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Batch code collision, try again")

    batch = Batch(
        id=batch_id,
        manufacturer_id=payload.manufacturer_id,
        drug_name=payload.drug_name,
        manufacturer_name=payload.manufacturer_name,
        draper_reg_no=payload.draper_reg_no,
        batch_number=payload.batch_number,
        manufacture_date=payload.manufacture_date,
        expiry_date=payload.expiry_date,
        signed_code=signed_code,
    )
    db.add(batch)

    # Log scan (first registration scan)
    ip = get_client_ip(request)
    scan = Scan(
        batch_id=batch.id,
        signed_code_scanned=signed_code,
        ip_address=ip,
        result="genuine",
    )
    db.add(scan)

    await db.commit()
    await db.refresh(batch)

    # Generate QR code URL
    verify_url = f"https://medverify.app/verify/{signed_code}"
    qr_response = generate_qr_code(verify_url)

    # Audit log
    await log_audit(
        db, "batch_registered", "batch", batch.id, manufacturer.id, request
    )
    await db.commit()

    return BatchResponse(
        id=batch.id,
        manufacturer_id=batch.manufacturer_id,
        drug_name=batch.drug_name,
        manufacturer_name=batch.manufacturer_name,
        draper_reg_no=batch.draper_reg_no,
        batch_number=batch.batch_number,
        manufacture_date=batch.manufacture_date,
        expiry_date=batch.expiry_date,
        signed_code=batch.signed_code,
        created_at=batch.created_at,
    )


@router.post("/manufacturers", response_model=ManufacturerResponse, status_code=201)
async def register_manufacturer(
    payload: ManufacturerCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    # Check for duplicate DRAP license number
    existing = await db.execute(
        select(Manufacturer).where(Manufacturer.drap_license_no == payload.drap_license_no)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Manufacturer with this DRAP license number already exists"
        )

    manufacturer = Manufacturer(
        name=payload.name,
        drap_license_no=payload.drap_license_no,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
    )
    db.add(manufacturer)
    await db.commit()
    await db.refresh(manufacturer)

    # Audit log
    await log_audit(
        db, "manufacturer_registered", "manufacturer", manufacturer.id, None, request
    )
    await db.commit()

    return ManufacturerResponse(
        id=manufacturer.id,
        name=manufacturer.name,
        drap_license_no=manufacturer.drap_license_no,
        contact_email=manufacturer.contact_email,
        contact_phone=manufacturer.contact_phone,
        created_at=manufacturer.created_at,
    )


@router.get("/manufacturers", response_model=list[ManufacturerResponse])
async def list_manufacturers(
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    result = await db.execute(select(Manufacturer))
    manufacturers = result.scalars().all()
    return [
        ManufacturerResponse(
            id=m.id,
            name=m.name,
            drap_license_no=m.drap_license_no,
            contact_email=m.contact_email,
            contact_phone=m.contact_phone,
            created_at=m.created_at,
        )
        for m in manufacturers
    ]


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.drap_license_no == payload.drap_license_no)
    )
    manufacturer = result.scalar_one_or_none()
    if not manufacturer:
        raise HTTPException(status_code=401, detail="Invalid DRAP license number")

    if manufacturer.password_hash and not verify_password(payload.password, manufacturer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    access_token = create_access_token(data={"sub": str(manufacturer.id)})
    refresh_token = create_refresh_token(data={"sub": str(manufacturer.id)})

    # Audit log
    await log_audit(db, "login", "manufacturer", manufacturer.id, manufacturer.id)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        manufacturer=ManufacturerResponse(
            id=manufacturer.id,
            name=manufacturer.name,
            drap_license_no=manufacturer.drap_license_no,
            contact_email=manufacturer.contact_email,
            contact_phone=manufacturer.contact_phone,
            created_at=manufacturer.created_at,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_async_db),
):
    from ..core.auth import verify_refresh_token
    manufacturer_id = verify_refresh_token(refresh_token)
    if manufacturer_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(Manufacturer).where(Manufacturer.id == manufacturer_id)
    )
    manufacturer = result.scalar_one_or_none()
    if not manufacturer or not manufacturer.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token(data={"sub": str(manufacturer.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(manufacturer.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        manufacturer=ManufacturerResponse(
            id=manufacturer.id,
            name=manufacturer.name,
            drap_license_no=manufacturer.drap_license_no,
            contact_email=manufacturer.contact_email,
            contact_phone=manufacturer.contact_phone,
            created_at=manufacturer.created_at,
        ),
    )


@router.get("/verify/{signed_code}")
@limiter.limit("60/minute")
async def verify_code(
    signed_code: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    ip = get_client_ip(request)
    now = datetime.utcnow()
    user_agent = request.headers.get("User-Agent")

    # Parse version from signed_code
    version = parse_signed_code(signed_code)
    if version != "v1":
        # Unknown version -> not_found (never suspicious for crypto failure)
        scan = Scan(
            signed_code_scanned=signed_code,
            ip_address=ip,
            result="not_found",
            user_agent=user_agent,
        )
        db.add(scan)
        await db.commit()
        return {"status": "not_found", "detail": "Code not registered or expired"}

    # Find batch by signed_code
    result = await db.execute(
        select(Batch).where(Batch.signed_code == signed_code)
    )
    batch = result.scalar_one_or_none()

    if not batch:
        # Log as not_found scan
        scan = Scan(
            signed_code_scanned=signed_code,
            ip_address=ip,
            result="not_found",
            user_agent=user_agent,
        )
        db.add(scan)
        await db.commit()
        return {"status": "not_found", "detail": "Code not registered or expired"}

    # Verify HMAC signature (constant-time comparison)
    if not verify_signature(
        signed_code,
        batch.id,
        batch.batch_number,
        batch.drug_name,
        batch.expiry_date,
    ):
        # Signature mismatch -> not_found (never suspicious for crypto failure)
        scan = Scan(
            signed_code_scanned=signed_code,
            ip_address=ip,
            result="not_found",
            user_agent=user_agent,
        )
        db.add(scan)
        await db.commit()
        return {"status": "not_found", "detail": "Code not registered or expired"}

    # Check batch status
    if batch.status != "active":
        scan = Scan(
            batch_id=batch.id,
            signed_code_scanned=signed_code,
            ip_address=ip,
            result="not_found",
            user_agent=user_agent,
        )
        db.add(scan)
        await db.commit()
        return {"status": "not_found", "detail": "Batch not found"}

    # Check recall
    if batch.recalled_at:
        scan = Scan(
            batch_id=batch.id,
            signed_code_scanned=signed_code,
            ip_address=ip,
            result="recalled",
            user_agent=user_agent,
        )
        db.add(scan)
        await db.commit()
        return {
            "status": "recalled",
            "detail": batch.recall_reason or "Batch has been recalled",
        }

    # Check expiry
    if batch.expiry_date and batch.expiry_date < now.date():
        scan = Scan(
            batch_id=batch.id,
            signed_code_scanned=signed_code,
            ip_address=ip,
            result="expired",
            user_agent=user_agent,
        )
        db.add(scan)
        await db.commit()
        return {"status": "expired", "detail": "Batch has expired"}

    # TODO: Check fraud rules (async, non-blocking) - if flagged -> "suspicious"
    # For now, log as genuine
    scan = Scan(
        batch_id=batch.id,
        signed_code_scanned=signed_code,
        ip_address=ip,
        result="genuine",
        user_agent=user_agent,
    )
    db.add(scan)
    await db.commit()

    # Audit log
    await log_audit(db, "verification", "batch", batch.id, request=request)
    await db.commit()

    return {
        "status": "genuine",
        "detail": f"Drug: {batch.drug_name}, Batch: {batch.batch_number}",
        "drug_name": batch.drug_name,
        "batch_number": batch.batch_number,
        "manufacture_date": batch.manufacture_date,
        "expiry_date": batch.expiry_date,
    }
