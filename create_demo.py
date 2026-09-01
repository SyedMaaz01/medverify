import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from medverify.core.auth import hash_password
from medverify.core.config import AsyncSessionLocal
from medverify.models import Manufacturer


async def create_demo():
    async with AsyncSessionLocal() as db:
        # Check existing
        from sqlalchemy import select
        result = await db.execute(select(Manufacturer).where(Manufacturer.drap_license_no == "DEMO-TEST-001"))
        existing = result.scalar_one_or_none()
        if existing:
            print("Demo user exists!")
            print("  DRAP License: DEMO-TEST-001")
            print("  Password: Demo@1234")
            return

        # Create demo user
        demo = Manufacturer(
            name="Demo Test User",
            drap_license_no="DEMO-TEST-001",
            contact_email="demo@test.com",
            password_hash=hash_password("Demo@1234"),
            role="manufacturer",
            is_active=True,
            is_verified=True,
            email_verified=True,
        )
        db.add(demo)
        await db.commit()
        print("Created demo user:")
        print("  DRAP License: DEMO-TEST-001")
        print("  Password: Demo@1234")

asyncio.run(create_demo())
