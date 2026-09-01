"""Demo seed data for local development and partner demos."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from medverify.core.auth import hash_password
from medverify.core.security import sign_batch_code
from medverify.models import Batch, Flag, Manufacturer, Scan, UserRole
from sqlalchemy.orm import Session

DEMO_MANUFACTURER = {
    "name": "DEMO PHARMA",
    "drap_license_no": "DEMO-LIC-0001",
    "contact_email": "demo@demopharma.example",
    "contact_phone": "+92-300-0000000",
}

ADMIN_USER = {
    "name": "DEMO ADMIN",
    "drap_license_no": "ADMIN-LIC-0001",
    "contact_email": "admin@medverify.example",
    "contact_phone": "+92-300-1111111",
    "password": "AdminPass123",
}

DEMO_BATCHES = [
    {
        "drug_name": "Demo Pain Relief 500mg",
        "batch_number": "DEMO-BATCH-001",
        "draper_reg_no": "DEMO-DRAP-001",
        "manufacture_date": date(2025, 1, 15),
        "expiry_date": date(2027, 1, 14),
    },
    {
        "drug_name": "Demo Antibiotic 250mg",
        "batch_number": "DEMO-BATCH-002",
        "draper_reg_no": "DEMO-DRAP-002",
        "manufacture_date": date(2024, 6, 1),
        "expiry_date": date(2025, 5, 31),  # expired — useful for verification UI testing
    },
    {
        "drug_name": "Demo Vitamin C 1000mg",
        "batch_number": "DEMO-BATCH-003",
        "draper_reg_no": "DEMO-DRAP-003",
        "manufacture_date": date(2025, 3, 1),
        "expiry_date": date(2028, 2, 29),
    },
]


def seed_demo_data(db: Session, *, force: bool = False) -> dict:
    """Insert obviously fake demo rows. Skips if DEMO PHARMA already exists unless force=True."""
    existing = (
        db.query(Manufacturer)
        .filter(Manufacturer.drap_license_no == DEMO_MANUFACTURER["drap_license_no"])
        .first()
    )
    if existing and not force:
        return {
            "skipped": True,
            "reason": "DEMO PHARMA already registered",
            "manufacturer_id": str(existing.id),
        }

    if existing and force:
        db.query(Scan).filter(
            Scan.batch_id.in_(db.query(Batch.id).filter(Batch.manufacturer_id == existing.id))
        ).delete(synchronize_session=False)
        db.query(Flag).filter(
            Flag.batch_id.in_(db.query(Batch.id).filter(Batch.manufacturer_id == existing.id))
        ).delete(synchronize_session=False)
        db.query(Batch).filter(Batch.manufacturer_id == existing.id).delete()
        db.query(Manufacturer).filter(Manufacturer.id == existing.id).delete()
        db.commit()

    now = datetime.now(UTC)
    manufacturer = Manufacturer(
        id=uuid.uuid4(),
        created_at=now,
        **DEMO_MANUFACTURER,
    )
    db.add(manufacturer)

    # Create admin user if not exists
    existing_admin = db.query(Manufacturer).filter(
        Manufacturer.drap_license_no == ADMIN_USER["drap_license_no"]
    ).first()
    if not existing_admin:
        admin = Manufacturer(
            id=uuid.uuid4(),
            name=ADMIN_USER["name"],
            drap_license_no=ADMIN_USER["drap_license_no"],
            contact_email=ADMIN_USER["contact_email"],
            contact_phone=ADMIN_USER["contact_phone"],
            password_hash=hash_password(ADMIN_USER["password"]),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
            email_verified=True,
            created_at=now,
            updated_at=now,
        )
        db.add(admin)

    db.flush()

    created_batches: list[dict] = []
    for spec in DEMO_BATCHES:
        batch_id = uuid.uuid4()
        signed_code = sign_batch_code(
            batch_id=batch_id,
            batch_number=spec["batch_number"],
            drug_name=spec["drug_name"],
            expiry_date=spec["expiry_date"],
        )
        batch = Batch(
            id=batch_id,
            manufacturer_id=manufacturer.id,
            manufacturer_name=manufacturer.name,
            signed_code=signed_code,
            created_at=now,
            **spec,
        )
        db.add(batch)
        db.flush()

        # One baseline scan per batch (registration-style)
        db.add(
            Scan(
                batch_id=batch.id,
                signed_code_scanned=signed_code,
                timestamp=now - timedelta(minutes=5),
                ip_address="127.0.0.1",
                approx_location="Karachi, PK",
                result="genuine" if spec["expiry_date"] >= now.date() else "expired",
            )
        )
        created_batches.append(
            {
                "batch_number": batch.batch_number,
                "signed_code": signed_code,
                "expiry_date": str(batch.expiry_date),
            }
        )

    # Synthetic fraud flag on the active batch (burst of scans)
    active_batch = (
        db.query(Batch)
        .filter(Batch.batch_number == "DEMO-BATCH-001")
        .one()
    )
    for i in range(6):
        db.add(
            Scan(
                batch_id=active_batch.id,
                signed_code_scanned=active_batch.signed_code,
                timestamp=now - timedelta(minutes=30 - i * 2),
                ip_address=f"203.0.113.{10 + i}",
                approx_location=["Karachi, PK", "Lahore, PK", "Islamabad, PK", "Peshawar, PK"][i % 4],
                result="genuine",
            )
        )
    db.add(
        Flag(
            batch_id=active_batch.id,
            reason="Scanned 6 times in 1 hour across 4 cities (demo seed)",
            created_at=now,
            resolved=False,
        )
    )

    db.commit()
    return {
        "skipped": False,
        "manufacturer_id": str(manufacturer.id),
        "admin_license": ADMIN_USER["drap_license_no"],
        "admin_password": ADMIN_USER["password"],
        "batches": created_batches,
    }
