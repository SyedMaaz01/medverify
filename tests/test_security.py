"""Tests for security module - HMAC signing and verification."""
import uuid
from datetime import date

from medverify.core.security import (
    SIGNING_KEY_VERSION,
    parse_signed_code,
    sign_batch_code,
    verify_signature,
)


class TestSignBatchCode:
    def test_sign_batch_code_returns_versioned_string(self):
        batch_id = uuid.uuid4()
        signed = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        assert signed.startswith(f"{SIGNING_KEY_VERSION}.")
        assert len(signed) > len(SIGNING_KEY_VERSION) + 1

    def test_sign_batch_code_deterministic(self):
        batch_id = uuid.uuid4()
        signed1 = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        signed2 = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        assert signed1 == signed2

    def test_sign_batch_code_different_inputs_produce_different_codes(self):
        batch_id = uuid.uuid4()
        signed1 = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        signed2 = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-002",  # different batch number
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        assert signed1 != signed2

    def test_sign_batch_code_different_expiry_produces_different_code(self):
        batch_id = uuid.uuid4()
        signed1 = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        signed2 = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-001",
            drug_name="Test Drug",
            expiry_date=date(2025, 12, 31),  # different expiry
        )
        assert signed1 != signed2


class TestVerifySignature:
    def test_verify_signature_valid(self):
        batch_id = uuid.uuid4()
        batch_number = "BATCH-001"
        drug_name = "Test Drug"
        expiry_date = date(2030, 12, 31)

        signed = sign_batch_code(batch_id, batch_number, drug_name, expiry_date)
        assert verify_signature(signed, batch_id, batch_number, drug_name, expiry_date)

    def test_verify_signature_invalid_batch_id(self):
        batch_id = uuid.uuid4()
        other_id = uuid.uuid4()
        batch_number = "BATCH-001"
        drug_name = "Test Drug"
        expiry_date = date(2030, 12, 31)

        signed = sign_batch_code(batch_id, batch_number, drug_name, expiry_date)
        assert not verify_signature(signed, other_id, batch_number, drug_name, expiry_date)

    def test_verify_signature_invalid_batch_number(self):
        batch_id = uuid.uuid4()
        batch_number = "BATCH-001"
        drug_name = "Test Drug"
        expiry_date = date(2030, 12, 31)

        signed = sign_batch_code(batch_id, batch_number, drug_name, expiry_date)
        assert not verify_signature(signed, batch_id, "BATCH-002", drug_name, expiry_date)

    def test_verify_signature_invalid_drug_name(self):
        batch_id = uuid.uuid4()
        batch_number = "BATCH-001"
        drug_name = "Test Drug"
        expiry_date = date(2030, 12, 31)

        signed = sign_batch_code(batch_id, batch_number, drug_name, expiry_date)
        assert not verify_signature(signed, batch_id, batch_number, "Other Drug", expiry_date)

    def test_verify_signature_invalid_expiry(self):
        batch_id = uuid.uuid4()
        batch_number = "BATCH-001"
        drug_name = "Test Drug"
        expiry_date = date(2030, 12, 31)

        signed = sign_batch_code(batch_id, batch_number, drug_name, expiry_date)
        assert not verify_signature(signed, batch_id, batch_number, drug_name, date(2025, 12, 31))

    def test_verify_signature_malformed_code(self):
        batch_id = uuid.uuid4()
        batch_number = "BATCH-001"
        drug_name = "Test Drug"
        expiry_date = date(2030, 12, 31)

        # Completely invalid code
        assert not verify_signature("invalid-code", batch_id, batch_number, drug_name, expiry_date)
        assert not verify_signature("v1.invalid", batch_id, batch_number, drug_name, expiry_date)
        assert not verify_signature("", batch_id, batch_number, drug_name, expiry_date)


class TestParseSignedCode:
    def test_parse_valid_code(self):
        batch_id = uuid.uuid4()
        signed = sign_batch_code(
            batch_id=batch_id,
            batch_number="BATCH-001",
            drug_name="Test Drug",
            expiry_date=date(2030, 12, 31),
        )
        version = parse_signed_code(signed)
        assert version == SIGNING_KEY_VERSION

    def test_parse_malformed_code(self):
        assert parse_signed_code("invalid") is None
        assert parse_signed_code("") is None
        assert parse_signed_code("v2.somecode") == "v2"
