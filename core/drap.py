from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class DRAPRegistration:
    registration_number: str
    drug_name: str
    manufacturer_name: str
    manufacturer_drap_license: str
    status: str
    expiry_date: date


class DRAPClient(ABC):
    @abstractmethod
    def lookup(self, registration_number: str) -> Optional[DRAPRegistration]:
        """Return registration record if valid and active, else None."""


class StubDRAPClient(DRAPClient):
    def lookup(self, registration_number: str) -> Optional[DRAPRegistration]:
        if not registration_number or not registration_number.strip():
            return None
        # Obviously fake data for demos
        if registration_number.startswith("DEMO-"):
            return DRAPRegistration(
                registration_number=registration_number,
                drug_name=f"DEMO DRUG {registration_number[-4:]}",
                manufacturer_name="DEMO PHARMA",
                manufacturer_drap_license="DEMO-LIC-001",
                status="active",
                expiry_date=date(2030, 12, 31),
            )
        return None


def get_drap_client() -> DRAPClient:
    """Dependency injection for DRAP client."""
    return StubDRAPClient()
