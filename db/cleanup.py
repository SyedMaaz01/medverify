"""Remove demo/test data from production database.

Usage:
    python -m medverify.db.cleanup --dry-run  # Preview what would be deleted
    python -m medverify.db.cleanup           # Actually delete
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from medverify.core.config import AsyncSessionLocal, async_engine
from medverify.models import Batch, Flag, Manufacturer, Scan, UserRole
from sqlalchemy import delete, select


DEMO_LICENSE_NOS = [
    "DEMO-LIC-0001",
    "ADMIN-LIC-0001",
]


async def cleanup(dry_run: bool = True) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Manufacturer).where(
                Manufacturer.drap_license_no.in_(DEMO_LICENSE_NOS)
            )
        )
        demo_manufacturers = result.scalars().all()

        if not demo_manufacturers:
            return {"deleted_manufacturers": 0, "deleted_batches": 0, "deleted_scans": 0, "deleted_flags": 0}

        deleted_manufacturers = 0
        deleted_batches = 0
        deleted_scans = 0
        deleted_flags = 0

        for mfr in demo_manufacturers:
            print(f"{'[DRY-RUN] Would delete' if dry_run else 'Deleting'} manufacturer: {mfr.name} ({mfr.drap_license_no})")

            result = await db.execute(select(Batch).where(Batch.manufacturer_id == mfr.id))
            batches = result.scalars().all()
            batch_ids = [b.id for b in batches]

            for batch in batches:
                print(f"  {'[DRY-RUN] Would delete' if dry_run else 'Deleting'} batch: {batch.batch_number}")

            if batch_ids:
                if not dry_run:
                    await db.execute(delete(Scan).where(Scan.batch_id.in_(batch_ids)))
                    await db.execute(delete(Flag).where(Flag.batch_id.in_(batch_ids)))
                    await db.execute(delete(Batch).where(Batch.id.in_(batch_ids)))
                deleted_batches += len(batch_ids)
                deleted_scans += len(batch_ids)
                deleted_flags += len(batch_ids)

            if not dry_run:
                await db.execute(delete(Manufacturer).where(Manufacturer.id == mfr.id))
            deleted_manufacturers += 1

        if not dry_run:
            await db.commit()

        return {
            "deleted_manufacturers": deleted_manufacturers,
            "deleted_batches": deleted_batches,
            "deleted_scans": deleted_scans,
            "deleted_flags": deleted_flags,
        }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Remove demo data from database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    args = parser.parse_args()

    result = await cleanup(dry_run=args.dry_run)

    print("\nSummary:")
    print(f"  Manufacturers: {result['deleted_manufacturers']}")
    print(f"  Batches: {result['deleted_batches']}")
    print(f"  Scans: {result['deleted_scans']}")
    print(f"  Flags: {result['deleted_flags']}")

    if args.dry_run:
        print("\nRun without --dry-run to actually delete.")

    await async_engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
