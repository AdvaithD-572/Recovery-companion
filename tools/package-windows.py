"""Build the offline Windows station from the tested project venv on Windows."""
import argparse
import importlib.metadata as metadata
import os
from pathlib import Path
import sys
import zipfile

from pip._vendor.packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "Recovery-Companion-Windows.zip"


def runtime_distributions():
    pending = [Requirement(s) for s in (
        "fastapi", "uvicorn", "sqlalchemy[asyncio]", "aiosqlite", "asyncpg", "alembic",
        "pydantic[email]", "pydantic-settings", "python-jose[cryptography]", "passlib",
        "bcrypt", "redis", "google-genai", "python-multipart", "httpx", "tzdata")]
    visited = set()
    included = {}
    while pending:
        req = pending.pop()
        dist = metadata.distribution(req.name)
        name = dist.metadata["Name"]
        extras = tuple(sorted(req.extras))
        if (name, extras) in visited:
            continue
        visited.add((name, extras))
        included[name] = dist
        for raw in dist.requires or ():
            dep = Requirement(raw)
            if not dep.marker or any(dep.marker.evaluate({"extra": extra}) for extra in ("", *extras)):
                pending.append(dep)
    return included.values()


def write_tree(archive, source, destination, skip=()):
    for path in source.rglob("*"):
        rel = path.relative_to(source)
        if path.is_file() and not any(part in (*skip, "__pycache__") for part in rel.parts):
            if path.suffix != ".pyc":
                archive.write(path, destination / rel)


def build(archive):
    base = Path(sys.base_prefix)
    runtime = Path("runtime")
    for path in [base / "python.exe", base / "LICENSE.txt", *base.glob("*.dll")]:
        archive.write(path, runtime / path.name)
    write_tree(archive, base / "DLLs", runtime / "DLLs")
    write_tree(archive, base / "Lib", runtime / "Lib", ("site-packages", "test","tests","idlelib","ensurepip","tkinter","turtledemo"))
    version = f"python{sys.version_info.major}{sys.version_info.minor}._pth"
    archive.writestr(str(runtime / version), ".\nLib\nDLLs\npackages\n../backend\nimport site\n")
    seen = set()
    for dist in runtime_distributions():
        for file in dist.files or ():
            if ".." in file.parts or "__pycache__" in file.parts or file.suffix == ".pyc":
                continue
            path = Path(dist.locate_file(file))
            if file not in seen and path.is_file():
                archive.write(path, runtime / "packages" / file)
                seen.add(file)
    for folder in ("app","alembic"):
        write_tree(archive, ROOT/"backend"/folder, Path("backend")/folder)
    for name in ("alembic.ini","demo.py","station.py","manage.py",".env.example"):
        archive.write(ROOT/"backend"/name, "backend/"+name)
    for title, cmd in (("Open sample clinic","demo.py"),("Open my clinic","station.py start"),
                       ("Create station administrator","station.py add-admin"), ("Add clinic staff","station.py add-staff")):
        archive.writestr(title+".cmd",'@echo off\r\ncd /d "%~dp0backend"\r\n"..\\runtime\\python.exe" -X utf8 -u '+cmd+'\r\nif errorlevel 1 pause\r\n')
    archive.write(ROOT/"docs/demo/follow-up.pdf","Sample follow-up.pdf")
    archive.write(ROOT/"docs/Windows quick start.txt","START HERE.txt")


if __name__ == "__main__":
    if sys.platform != "win32" or sys.prefix == sys.base_prefix:
        raise SystemExit("Run with the backend Windows virtual environment.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-android", action="store_true", help="Include the signed APK in the Windows kit")
    args = parser.parse_args()
    apk = ROOT/"dist/app-release.apk"
    if args.include_android:
        if not apk.is_file():
            parser.error("Build the signed Android APK first.")
        OUTPUT = OUTPUT.with_name("Recovery-Companion.zip")
    OUTPUT.parent.mkdir(exist_ok=True)
    from uuid import uuid4
    target = OUTPUT.with_suffix('.' + uuid4().hex + '.partial')
    try:
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
            build(archive)
            if args.include_android:
                archive.write(apk, 'Recovery-Companion-Android.apk', compress_type=zipfile.ZIP_STORED)
        os.replace(target, OUTPUT)
    finally:
        target.unlink(missing_ok=True)
    print("Built dist/" + OUTPUT.name)
