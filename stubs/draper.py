"""Stub DRAP registration-number lookup.

For MVP: returns dummy data. Replace with real API/partnership feed later.
"""


def lookup(reg_no: str) -> dict:
    """Validate a DRAP registration number.

    Returns {
        "valid": bool,
        "message": str,
        "drug_name": Optional[str],
    }
    """
    # MVP stub: accept any non-empty string as valid
    if not reg_no or not reg_no.strip():
        return {"valid": False, "message": "Invalid DRAP registration number", "drug_name": None}
    return {
        "valid": True,
        "message": "DRAP registration verified (stub)",
        "drug_name": f"Sample Drug {reg_no[-4:]}",
    }
