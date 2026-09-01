import uuid
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import get_admin_user
from ..core.database import get_async_db
from ..models import Batch, Flag, Manufacturer, Scan
from ..schemas import FlagResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/batches")
async def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Batch).offset(offset).limit(page_size).order_by(Batch.created_at.desc())
    )
    batches = result.scalars().all()

    total_result = await db.execute(select(func.count(Batch.id)))
    total = total_result.scalar()

    return [
        {
            "id": str(b.id),
            "manufacturer_id": str(b.manufacturer_id),
            "drug_name": b.drug_name,
            "manufacturer_name": b.manufacturer_name,
            "draper_reg_no": b.draper_reg_no,
            "batch_number": b.batch_number,
            "manufacture_date": str(b.manufacture_date),
            "expiry_date": str(b.expiry_date),
            "signed_code": b.signed_code,
            "status": b.status,
            "scan_count": len(b.scans) if b.scans else 0,
        }
        for b in batches
    ]


@router.get("/batches/{batch_id}/scans")
async def list_scans(
    batch_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    batch_uuid = uuid.UUID(batch_id)
    offset = (page - 1) * page_size

    result = await db.execute(
        select(Scan)
        .where(Scan.batch_id == batch_uuid)
        .offset(offset)
        .limit(page_size)
        .order_by(Scan.timestamp.desc())
    )
    scans = result.scalars().all()

    total_result = await db.execute(
        select(func.count(Scan.id)).where(Scan.batch_id == batch_uuid)
    )
    total = total_result.scalar()

    return [
        {
            "id": str(s.id),
            "code": s.signed_code_scanned,
            "timestamp": s.timestamp,
            "ip_address": s.ip_address,
            "approx_location": s.approx_location,
            "result": s.result,
            "risk_score": s.risk_score,
        }
        for s in scans
    ]


@router.get("/suspicious")
async def flagged_suspicious(
    hours: int = Query(24, ge=1, le=168),
    threshold: int = Query(5, ge=1),
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    """Find codes scanned more than threshold times from different IPs within time window."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(Scan).where(Scan.timestamp >= cutoff)
    )
    scans = result.scalars().all()

    code_counts = Counter()
    code_locations = {}
    for s in scans:
        code_counts[s.signed_code_scanned] += 1
        if s.signed_code_scanned not in code_locations:
            code_locations[s.signed_code_scanned] = set()
        if s.ip_address:
            code_locations[s.signed_code_scanned].add(s.ip_address)

    flagged = []
    for code, count in code_counts.items():
        if count >= threshold:
            locations = code_locations.get(code, set())
            flagged.append(
                {
                    "code": code,
                    "scan_count": count,
                    "locations": list(locations),
                    "reason": f"Scanned {count} times in {hours}h from {len(locations)} locations",
                }
            )
    return flagged


@router.get("/flags", response_model=list[FlagResponse])
async def list_flags(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    offset = (page - 1) * page_size
    query = select(Flag).order_by(Flag.created_at.desc())
    if resolved is not None:
        query = query.where(Flag.resolved == resolved)
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    flags = result.scalars().all()

    return [
        FlagResponse(
            id=f.id,
            batch_id=f.batch_id,
            reason=f.reason,
            severity=f.severity,
            created_at=f.created_at,
            resolved=f.resolved,
            resolved_at=f.resolved_at,
            resolved_by=f.resolved_by,
        )
        for f in flags
    ]


@router.post("/flags/{flag_id}/resolve")
async def resolve_flag(
    flag_id: str,
    payload: dict = {},
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    flag_uuid = uuid.UUID(flag_id)
    result = await db.execute(select(Flag).where(Flag.id == flag_uuid))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    flag.resolved = True
    flag.resolved_at = datetime.utcnow()
    flag.resolved_by = current_user.id
    await db.commit()
    return {"status": "resolved"}


@router.get("/analytics/overview")
async def analytics_overview(
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    """Get overview analytics for dashboard."""
    # Total counts
    total_batches = await db.execute(select(func.count(Batch.id)))
    total_manufacturers = await db.execute(select(func.count(Manufacturer.id)))
    total_scans = await db.execute(select(func.count(Scan.id)))
    total_flags = await db.execute(select(func.count(Flag.id)))

    # Scans by result
    scans_by_result = await db.execute(
        select(Scan.result, func.count(Scan.id))
        .group_by(Scan.result)
    )
    result_counts = {row[0]: row[1] for row in scans_by_result.fetchall()}

    # Recent scans (last 24h)
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_scans = await db.execute(
        select(func.count(Scan.id)).where(Scan.timestamp >= cutoff)
    )

    return {
        "total_batches": total_batches.scalar(),
        "total_manufacturers": total_manufacturers.scalar(),
        "total_scans": total_scans.scalar(),
        "total_flags": total_flags.scalar(),
        "scans_by_result": result_counts,
        "recent_scans_24h": recent_scans.scalar(),
    }


@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: Manufacturer = Depends(get_admin_user),
):
    from ..models import AuditLog
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog)
        .offset(offset)
        .limit(page_size)
        .order_by(AuditLog.timestamp.desc())
    )
    logs = result.scalars().all()

    total_result = await db.execute(select(func.count(AuditLog.id)))
    total = total_result.scalar()

    return {
        "items": [
            {
                "id": str(l.id),
                "user_id": str(l.user_id) if l.user_id else None,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": str(l.resource_id) if l.resource_id else None,
                "ip_address": l.ip_address,
                "timestamp": l.timestamp,
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }
