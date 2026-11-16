"""Local clinic provisioning. Run from backend with the project virtualenv."""
import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select
from app.main import app
from app.core.database import engine, AsyncSessionLocal
from app.core.security import hash_password
from app.models import Clinician
from app.care import Staff
from app.registry import Clinic


async def add_admin(email=None):
    from app.core.migrations import migrate
    await migrate(engine)
    from pydantic import EmailStr, TypeAdapter
    from app.registry import Administrator, DirectoryAudit
    email = str(TypeAdapter(EmailStr).validate_python((email or input("Administrator email: ")).strip())).lower()
    password = getpass.getpass("Administrator password (12+ characters): ") if sys.stdin.isatty() else sys.stdin.readline().rstrip("\r\n")
    if len(password) < 12 or len(password.encode()) > 72:
        raise SystemExit("Use at least 12 characters and at most 72 bytes.")
    async with AsyncSessionLocal.begin() as db:
        if await db.scalar(select(Administrator.id).where(Administrator.email == email)):
            raise SystemExit("Administrator email already exists.")
        admin = Administrator(email=email, hashed_password=hash_password(password))
        db.add(admin)
        await db.flush()
        db.add(DirectoryAudit(actor=admin.id, action="local_admin_created", target=admin.id))
    await engine.dispose()
    print("Administrator created. Open /clinic/admin.html to manage clinics.")


async def provision(args):
    if sys.stdin.isatty():
        password = getpass.getpass("New staff password (12+ characters): ")
    else:
        # Redirected stdin supports local provisioning without exposing a secret in process arguments.
        password = sys.stdin.readline().rstrip("\r\n")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters")
    from app.core.migrations import migrate
    await migrate(engine)
    async with AsyncSessionLocal.begin() as db:
        scope = await db.scalar(select(Clinic.scope).where(Clinic.name == args.clinic, Clinic.deleted_at.is_(None)).with_for_update(read=True))
        if not scope:
            raise SystemExit("Create this clinic in the administrator portal first.")
        if await db.scalar(select(Clinician.id).where(Clinician.email == args.email)):
            raise SystemExit("Staff email already exists")
        account = Clinician(full_name=args.name, email=args.email, hashed_password=hash_password(password))
        db.add(account)
        await db.flush()
        db.add(Staff(id=account.id, clinic=scope, role=args.role))
    print("Clinic account created.")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name")
    parser.add_argument("--clinic")
    parser.add_argument("--role", choices=["administrator", "clinician", "receptionist"], required=True)
    args = parser.parse_args()
    if args.role == "administrator":
        asyncio.run(add_admin(args.email))
    elif args.name and args.clinic:
        asyncio.run(provision(args))
    else:
        parser.error("Supply --name and --clinic for clinic staff.")
