import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from medverify.core.config import AsyncSessionLocal, async_engine
from medverify.models import Manufacturer
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Manufacturer))
        for u in result.scalars().all():
            print(f"username={u.drap_license_no} | name={u.name} | email={u.contact_email} | role={u.role.value} | active={u.is_active} | verified={u.is_verified} | email_verified={u.email_verified} | has_password={bool(u.password_hash)} | 2fa={u.totp_enabled}")
    await async_engine.dispose()

asyncio.run(main())
