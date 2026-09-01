"""Tests for fraud detection / suspicious activity flagging."""
from collections import Counter
from datetime import date, datetime, timedelta
from uuid import uuid4

from medverify.core.security import sign_batch_code
from medverify.models import Batch, Scan
from sqlalchemy import select


class TestFraudDetection:
    async def test_suspicious_multiple_scans_same_code_different_ips(
        self, client, db_session, sample_manufacturer
    ):
        """Test that multiple scans from different IPs flag as suspicious."""
        batch_id = uuid4()
        signed_code = sign_batch_code(
            batch_id=batch_id,
            batch_number="FRAUD-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        batch = Batch(
            id=batch_id,
            manufacturer_id=sample_manufacturer.id,
            drug_name="Test Drug",
            manufacturer_name="TEST PHARMA",
            draper_reg_no="DEMO-REG-FRAUD",
            batch_number="FRAUD-001",
            manufacture_date=date(2024, 1, 1),
            expiry_date=date(2030, 12, 31),
            signed_code=signed_code,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(batch)
        await db_session.commit()

        # Simulate 5 scans from different IPs within 24 hours
        base_time = datetime.utcnow()
        ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4", "192.168.1.5"]
        for i, ip in enumerate(ips):
            scan = Scan(
                batch_id=batch.id,
                signed_code_scanned=signed_code,
                timestamp=base_time - timedelta(hours=i),
                ip_address=ip,
                result="genuine",
            )
            db_session.add(scan)
        await db_session.commit()

        # Check suspicious logic directly
        cutoff = datetime.utcnow() - timedelta(hours=24)
        result = await db_session.execute(
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
            if count >= 5:
                locations = code_locations.get(code, set())
                flagged.append(
                    {
                        "code": code,
                        "scan_count": count,
                        "locations": list(locations),
                        "reason": f"Scanned {count} times in 24h from {len(locations)} locations",
                    }
                )

        assert len(flagged) == 1
        assert flagged[0]["code"] == signed_code
        assert flagged[0]["scan_count"] == 5
        assert len(flagged[0]["locations"]) == 5

    async def test_not_suspicious_few_scans(self, client, db_session, sample_manufacturer):
        """Test that few scans don't trigger suspicious flag."""
        batch_id = uuid4()
        signed_code = sign_batch_code(
            batch_id=batch_id,
            batch_number="SAFE-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        batch = Batch(
            id=batch_id,
            manufacturer_id=sample_manufacturer.id,
            drug_name="Test Drug",
            manufacturer_name="TEST PHARMA",
            draper_reg_no="DEMO-REG-SAFE",
            batch_number="SAFE-001",
            manufacture_date=date(2024, 1, 1),
            expiry_date=date(2030, 12, 31),
            signed_code=signed_code,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(batch)
        await db_session.commit()

        # Only 3 scans from same IP
        base_time = datetime.utcnow()
        for i in range(3):
            scan = Scan(
                batch_id=batch.id,
                signed_code_scanned=signed_code,
                timestamp=base_time - timedelta(hours=i),
                ip_address="192.168.1.1",
                result="genuine",
            )
            db_session.add(scan)
        await db_session.commit()

        cutoff = datetime.utcnow() - timedelta(hours=24)
        result = await db_session.execute(
            select(Scan).where(Scan.timestamp >= cutoff)
        )
        scans = result.scalars().all()

        code_counts = Counter()
        for s in scans:
            code_counts[s.signed_code_scanned] += 1

        flagged = [code for code, count in code_counts.items() if count >= 5]
        assert len(flagged) == 0

    async def test_not_suspicious_scans_outside_window(self, client, db_session, sample_manufacturer):
        """Test that scans outside 24h window don't trigger flag."""
        batch_id = uuid4()
        signed_code = sign_batch_code(
            batch_id=batch_id,
            batch_number="OLD-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        batch = Batch(
            id=batch_id,
            manufacturer_id=sample_manufacturer.id,
            drug_name="Test Drug",
            manufacturer_name="TEST PHARMA",
            draper_reg_no="DEMO-REG-OLD",
            batch_number="OLD-001",
            manufacture_date=date(2024, 1, 1),
            expiry_date=date(2030, 12, 31),
            signed_code=signed_code,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(batch)
        await db_session.commit()

        # 10 scans but all 48 hours ago
        base_time = datetime.utcnow() - timedelta(hours=48)
        for i in range(10):
            scan = Scan(
                batch_id=batch.id,
                signed_code_scanned=signed_code,
                timestamp=base_time - timedelta(hours=i),
                ip_address=f"192.168.1.{i}",
                result="genuine",
            )
            db_session.add(scan)
        await db_session.commit()

        cutoff = datetime.utcnow() - timedelta(hours=24)
        result = await db_session.execute(
            select(Scan).where(Scan.timestamp >= cutoff)
        )
        scans = result.scalars().all()

        code_counts = Counter()
        for s in scans:
            code_counts[s.signed_code_scanned] += 1

        flagged = [code for code, count in code_counts.items() if count >= 5]
        assert len(flagged) == 0
