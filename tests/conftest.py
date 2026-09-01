import os
import sys
import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from medverify.core.database import get_async_db
from medverify.main import app
from medverify.models import Base

# Use a shared temp file so the DB persists across sessions within one test run
_tmp_dir = tempfile.mkdtemp(prefix="medverify_test_")
_TEST_DB_PATH = os.path.join(_tmp_dir, "test.sqlite3")
_TEST_DB_URL = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"

test_async_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingAsyncSessionLocal = async_sessionmaker(
    test_async_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


async def override_get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables once for the entire test session."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_async_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh session and clean up tables after each test."""
    async with TestingAsyncSessionLocal() as session:
        yield session
    # Clean all data between tests
    async with test_async_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with overridden database."""
    app.dependency_overrides[get_async_db] = override_get_async_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_manufacturer(db_session) -> "Manufacturer":
    """Create a sample manufacturer for testing."""
    import uuid as uuid_lib

    from medverify.models import Manufacturer

    manufacturer = Manufacturer(
        id=uuid_lib.uuid4(),
        name="TEST PHARMA",
        drap_license_no=f"TEST-LIC-{uuid_lib.uuid4().hex[:8]}",
        contact_email="test@testpharma.com",
        contact_phone="+92-300-1234567",
        is_active=True,
        is_verified=False,
        email_verified=True,
        password_hash="dummy_hash",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(manufacturer)
    await db_session.commit()
    await db_session.refresh(manufacturer)
    return manufacturer


@pytest_asyncio.fixture
async def sample_batch(db_session, sample_manufacturer) -> "Batch":
    """Create a sample batch for testing."""
    import uuid as uuid_lib

    from medverify.core.security import sign_batch_code
    from medverify.models import Batch

    batch_id = uuid_lib.uuid4()
    batch_number = f"BATCH-{uuid_lib.uuid4().hex[:8]}"
    signed_code = sign_batch_code(
        batch_id=batch_id,
        batch_number=batch_number,
        drug_name="Test Drug",
        expiry_date=date(2030, 12, 31),
    )

    batch = Batch(
        id=batch_id,
        manufacturer_id=sample_manufacturer.id,
        drug_name="Test Drug",
        manufacturer_name="TEST PHARMA",
        draper_reg_no="DEMO-REG-001",
        batch_number=batch_number,
        manufacture_date=date(2024, 1, 1),
        expiry_date=date(2030, 12, 31),
        signed_code=signed_code,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(batch)
    await db_session.commit()
    await db_session.refresh(batch)
    return batch
