"""Local Windows clinic station, with a persistent database and an offline backup path."""
import argparse
import asyncio
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import threading
import webbrowser


def backup(source, destination):
    if not source.is_file():
        raise SystemExit("Database missing.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Publish a verified copy atomically. An existing backup is never overwritten.
    with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
        copy = Path(staging) / "copy.db"
        from contextlib import closing
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            with closing(sqlite3.connect(copy)) as out:
                db.backup(out)
                if out.execute("pragma integrity_check").fetchall() != [("ok",)]:
                    raise SystemExit("Backup integrity check failed.")
                if not out.execute("select 1 from sqlite_master where name='patients'").fetchone():
                    raise SystemExit("This is not a Recovery Companion database.")
        os.link(copy, destination)


def configure(folder):
    folder.mkdir(parents=True, exist_ok=True)
    config = folder / ".env"
    if not config.exists():
        try:
            with config.open("x", encoding="utf-8") as file:
                file.write("SECRET_KEY=" + secrets.token_urlsafe(48) + "\nGEMINI_API_KEY=\nGEMINI_MODEL=gemini-flash-latest\n")
        except FileExistsError:
            pass
    # Resolve settings relative to this operator's directory even from a shortcut.
    os.chdir(folder)
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (folder / "clinic.db").as_posix()
    os.environ["ENVIRONMENT"] = "production"
    os.environ["ALLOWED_HOSTS"] = "127.0.0.1,localhost,10.0.2.2"
    return config


async def needs_admin():
    from sqlalchemy import select
    from app.registry import Administrator
    from app.core.database import AsyncSessionLocal, engine
    async with AsyncSessionLocal() as db:
        first = await db.scalar(select(Administrator.id).limit(1))
    await engine.dispose()
    return first is None


def add_staff():
    from pydantic import EmailStr, TypeAdapter
    from manage import provision
    role = input("Role [clinician or receptionist, default clinician]: ").strip() or "clinician"
    if role not in ("clinician", "receptionist"):
        raise SystemExit("Unknown staff role.")
    name = input("Staff full name: ").strip()
    clinic = input("Clinic name: ").strip()
    email = str(TypeAdapter(EmailStr).validate_python(input("Staff email: ").strip())).lower()
    if not name or not clinic:
        raise SystemExit("Staff and clinic names are required.")
    asyncio.run(provision(argparse.Namespace(name=name, clinic=clinic, role=role, email=email)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start","add-admin","add-staff","backup","restore"], nargs="?", default="start")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path(os.getenv("LOCALAPPDATA",Path.home()))/"RecoveryCompanion"/"clinic")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    folder = args.data_dir.resolve()
    db = folder / "clinic.db"
    if args.action in ("backup","restore"):
        if args.file is None:
            parser.error("Supply a backup filename.")
        if args.action == "restore" and db.exists():
            parser.error("Restore requires a new data directory.")
        if args.action == 'backup':
            backup(db, args.file.resolve())
        else:
            backup(args.file.resolve(), db)
        print("Verified database copy created.")
        return
    config = configure(folder)
    from app.core.migrations import migrate
    from app.core.database import engine
    asyncio.run(migrate(engine))
    if args.action == "add-admin" or (args.action == "start" and asyncio.run(needs_admin())):
        from manage import add_admin
        asyncio.run(add_admin())
    if args.action == "add-staff":
        add_staff()
    if args.action == "start":
        from app.main import app
        import uvicorn
        url = f"http://127.0.0.1:{args.port}/clinic/"
        print("Clinic desk:", url, "\nDatabase:", db, "\nLocal settings:", config, flush=True)
        if not args.no_browser:
            threading.Timer(1.5, webbrowser.open, args=(url,)).start()
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
