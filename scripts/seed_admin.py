"""Seed a super admin user for the MedVerify application."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from medverify.core.auth import hash_password
from medverify.core.config import AsyncSessionLocal, async_engine
from medverify.models import Manufacturer, UserRole
from sqlalchemy import select


async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Manufacturer).where(
                Manufacturer.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])
            )
        )
        existing = result.scalars().all()
        if existing:
            print("Admin user(s) already exist:")
            for u in existing:
                print(f"  - {u.name} ({u.contact_email}) role={u.role.value}")
            return

        email = "admin@medverify.pk"
        license_no = "ADMIN-001"
        password = "Admin@12345"

        admin = Manufacturer(
            name="System Administrator",
            drap_license_no=license_no,
            contact_email=email,
            password_hash=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
            email_verified=True,
        )
        db.add(admin)
        await db.commit()
        print("Created super admin:")
        print(f"  Username (DRAP license): {license_no}")
        print(f"  Password: {password}")
        print(f"  Email: {email}")


async def main():
    await seed()
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
