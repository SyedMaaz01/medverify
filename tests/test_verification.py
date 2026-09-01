"""Tests for verification endpoint."""
from datetime import date, datetime
from uuid import uuid4

from medverify.core.security import sign_batch_code
from medverify.models import Batch, Scan
from sqlalchemy import func, select


class TestVerifyEndpoint:
    async def test_verify_genuine_batch(self, client, sample_batch):
        response = client.get(f"/api/verify/{sample_batch.signed_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "genuine"
        assert data["drug_name"] == "Test Drug"
        assert data["batch_number"] == sample_batch.batch_number

    async def test_verify_expired_batch(self, client, db_session, sample_manufacturer):
        """Test that expired batch returns expired status."""
        batch_id = uuid4()
        past_date = date(2020, 1, 1)
        batch_number = f"EXPIRED-{uuid4().hex[:8]}"
        signed_code = sign_batch_code(
            batch_id=batch_id,
            batch_number=batch_number,
            drug_name="Expired Drug",
            expiry_date=past_date,
        )
        batch = Batch(
            id=batch_id,
            manufacturer_id=sample_manufacturer.id,
            drug_name="Expired Drug",
            manufacturer_name="TEST PHARMA",
            draper_reg_no="DEMO-REG-002",
            batch_number=batch_number,
            manufacture_date=date(2020, 1, 1),
            expiry_date=past_date,
            signed_code=signed_code,
            created_at=datetime(2020, 1, 1),
            updated_at=datetime(2020, 1, 1),
            status="active",
        )
        db_session.add(batch)
        await db_session.commit()

        response = client.get(f"/api/verify/{signed_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "expired"

    async def test_verify_not_found_invalid_code(self, client):
        """Test that non-existent code returns not_found."""
        response = client.get("/api/verify/v1.invalidcode")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"

    async def test_verify_not_found_wrong_signature(self, client, db_session, sample_manufacturer):
        """Test that code with wrong signature returns not_found."""
        batch_id = uuid4()
        signed_code = sign_batch_code(
            batch_id=batch_id,
            batch_number="TAMPERED-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        batch = Batch(
            id=batch_id,
            manufacturer_id=sample_manufacturer.id,
            drug_name="Different Drug",
            manufacturer_name="TEST PHARMA",
            draper_reg_no="DEMO-REG-003",
            batch_number="TAMPERED-001",
            manufacture_date=date(2024, 1, 1),
            expiry_date=date(2030, 12, 31),
            signed_code=signed_code,
            created_at=date(2024, 1, 1),
            updated_at=date(2024, 1, 1),
            status="active",
        )
        db_session.add(batch)
        await db_session.commit()

        response = client.get(f"/api/verify/{signed_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"

    async def test_verify_logs_scan(self, client, db_session, sample_batch):
        """Test that verification logs a scan."""
        result = await db_session.execute(select(func.count(Scan.id)))
        initial_scan_count = result.scalar()

        response = client.get(f"/api/verify/{sample_batch.signed_code}")
        assert response.status_code == 200

        result = await db_session.execute(select(func.count(Scan.id)))
        final_scan_count = result.scalar()
        assert final_scan_count == initial_scan_count + 1

        result = await db_session.execute(
            select(Scan).order_by(Scan.timestamp.desc()).limit(1)
        )
        scan = result.scalar_one()
        assert scan.signed_code_scanned == sample_batch.signed_code
        assert scan.batch_id == sample_batch.id
        assert scan.result == "genuine"

    async def test_verify_unknown_version(self, client):
        """Test that unknown version returns not_found."""
        response = client.get("/api/verify/v99.fakecode")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"

    async def test_verify_rate_limit(self, client, sample_batch):
        """Test rate limiting on verify endpoint."""
        for _ in range(60):
            response = client.get(f"/api/verify/{sample_batch.signed_code}")
            assert response.status_code == 200

        response = client.get(f"/api/verify/{sample_batch.signed_code}")
        assert response.status_code == 429
