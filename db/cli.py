"""CLI for database migrations and seeding.

Usage (from project/):
    python -m medverify.db.cli migrate
    python -m medverify.db.cli seed
    python -m medverify.db.cli seed --force
    python -m medverify.db.cli status
"""

from __future__ import annotations

import argparse
from pathlib import Path

from medverify.core.config import SQLALCHEMY_DATABASE_URL, SessionLocal
from medverify.core.config import sync_engine as engine
from medverify.db.seed import seed_demo_data
from sqlalchemy import inspect, text

from alembic import command
from alembic.config import Config

PACKAGE_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    cfg = Config(str(PACKAGE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(PACKAGE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
    return cfg


def cmd_migrate(_: argparse.Namespace) -> int:
    command.upgrade(_alembic_config(), "head")
    print(f"Migrations applied. Database: {SQLALCHEMY_DATABASE_URL}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    print(f"Database URL: {SQLALCHEMY_DATABASE_URL}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables ({len(tables)}): {', '.join(sorted(tables)) or '(none)'}")
    with engine.connect() as conn:
        if "alembic_version" in tables:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print(f"Alembic revision: {version}")
        for table in ("manufacturers", "batches", "scans", "flags"):
            if table in tables:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  {table}: {count} rows")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        result = seed_demo_data(db, force=args.force)
    finally:
        db.close()
    if result.get("skipped"):
        print(result["reason"])
    else:
        print("Demo data seeded:")
        print(f"  manufacturer_id: {result['manufacturer_id']}")
        for batch in result["batches"]:
            print(f"  {batch['batch_number']} -> {batch['signed_code']} (exp {batch['expiry_date']})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MedVerify database management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="Apply Alembic migrations (upgrade head)")
    sub.add_parser("status", help="Show database URL, tables, and row counts")

    seed_parser = sub.add_parser("seed", help="Insert DEMO PHARMA demo data")
    seed_parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing DEMO PHARMA data before seeding",
    )

    args = parser.parse_args(argv)
    handlers = {
        "migrate": cmd_migrate,
        "status": cmd_status,
        "seed": cmd_seed,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
