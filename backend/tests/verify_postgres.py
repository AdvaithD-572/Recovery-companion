"""Rehearse the migration and workflow on a disposable loopback PostgreSQL cluster."""
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    binaries = Path(os.environ["PG_BIN"]) if "PG_BIN" in os.environ else Path(shutil.which("initdb") or "").parent
    with tempfile.TemporaryDirectory(prefix="recovery-pg-") as folder:
        data = Path(folder) / "cluster"
        password = secrets.token_hex(24)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        pwfile = Path(folder) / "bootstrap-password"
        pwfile.write_text(password + "\n", encoding="ascii")
        subprocess.run([str(binaries / "initdb"), "-D", str(data), "-U", "rc_test", "-A",
                        "scram-sha-256", "--encoding=UTF8", "--locale=C", f"--pwfile={pwfile}"], check=True)
        pwfile.unlink()
        ctl = [str(binaries / "pg_ctl"), "-D", str(data), "-w"]
        subprocess.run(ctl + ["-l", str(Path(folder) / "server.log"), "-o", f"-h 127.0.0.1 -p {port}", "start"], check=True)
        try:
            pg = dict(os.environ, PGHOST="127.0.0.1", PGPORT=str(port), PGUSER="rc_test", PGPASSWORD=password)
            def run_pg(tool, *args, capture=False):
                return subprocess.run([str(binaries/tool), *args], env=pg, check=True, text=True, capture_output=capture)
            run_pg("createdb", "rc_rehearsal")
            url = f"postgresql+asyncpg://rc_test:{password}@127.0.0.1:{port}/rc_rehearsal"
            env = dict(os.environ, DATABASE_URL=url, RC_ISOLATED_TEST_DATABASE=url, GEMINI_API_KEY="")
            backend = Path(__file__).resolve().parents[1]
            fixture = """
import asyncio
from datetime import date
from app.core.database import Base, engine, AsyncSessionLocal
from app.models import Patient, DailyLog
async def seed():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal.begin() as db:
        p = Patient(full_name='Historical fixture', email='archive@example.org', hashed_password='disabled')
        db.add(p)
        await db.flush()
        db.add(DailyLog(patient_id=p.id, log_date=date(2020,2,29), pain_score=2, note='Historical entry'))
    await engine.dispose()
asyncio.run(seed())
"""
            subprocess.run([sys.executable, "-c", fixture], cwd=backend, env=env, check=True)
            def row_fingerprint(db):
                return run_pg("psql", "-XAt", "-d", db, "-c",
                    "select p.id, p.created_at, l.id, l.created_at, l.log_date, l.note, l.pain_score from patients p join daily_logs l on p.id=l.patient_id where p.email='archive@example.org'",
                    capture=True).stdout.strip()
            original = row_fingerprint("rc_rehearsal")
            if "Historical entry" not in original:
                raise AssertionError("Historical fixture missing")
            subprocess.run([sys.executable, "-m", "alembic", "upgrade", "0001"], cwd=backend, env=env, check=True)
            run_pg("psql", "-d", "rc_rehearsal", "-v", "ON_ERROR_STOP=1", "-c",
                   "insert into care_links(patient,clinic) select id,'Historical clinic' from patients where email='archive@example.org'")
            for args in (["alembic", "upgrade", "head"], ["alembic", "check"],
                         ["unittest", "discover", "-s", "tests", "-q"]):
                subprocess.run([sys.executable, "-m", *args], env=env, check=True,
                               cwd=Path(__file__).resolve().parents[1])
            if row_fingerprint("rc_rehearsal") != original:
                raise AssertionError("Migration changed historical records")
            legacy_clinic = run_pg("psql", "-XAt", "-d", "rc_rehearsal", "-c",
                "select c.name from care_clinics c join care_links l on l.clinic=c.scope where c.name='Historical clinic'", capture=True)
            if legacy_clinic.stdout.strip() != "Historical clinic":
                raise AssertionError("Historical clinic link was lost")
            dump = str(Path(folder)/"backup.dump")
            run_pg("pg_dump", "-Fc", "-d", "rc_rehearsal", "-f", dump)
            run_pg("createdb", "rc_restored")
            run_pg("pg_restore","--exit-on-error","--single-transaction","-d","rc_restored",dump)
            def ledger(db):
                return run_pg("psql", "-XAt", "-d", db, "-c",
                    "select md5(string_agg(to_jsonb(r)::text, '' order by r.id)) from care_records r",
                    capture=True).stdout.strip()
            if row_fingerprint("rc_restored") != original or not ledger("rc_rehearsal") or ledger("rc_restored") != ledger("rc_rehearsal"):
                raise AssertionError("Restored diary or clinic ledger differs from the original")
            print("Historical migration and populated PostgreSQL backup/restore verified.")
        finally:
            subprocess.run(ctl + ["-m", "fast", "stop"], check=True)


if __name__ == "__main__":
    main()
