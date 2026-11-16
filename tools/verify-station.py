"""Exercise the extracted Windows package, then back up and reopen a synthetic station."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile


def main():
    archive = Path(__file__).resolve().parents[1] / "dist/Recovery-Companion-Windows.zip"
    if len(sys.argv) == 2:
        archive = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="rc-station-test-") as temp:
        root = Path(temp)
        with zipfile.ZipFile(archive) as package:
            assert package.testzip() is None
            assert not any(Path(name).name in {".env","clinic.db"} for name in package.namelist())
            package.extractall(root)
        python = str(root/"runtime/python.exe")
        station = str(root/"backend/station.py")
        env = dict(os.environ, GEMINI_API_KEY="", PYTHONUTF8="1")
        folder = root/"operator"
        password = secrets.token_urlsafe(18)
        cli = [python, "-X","utf8", station]
        create = subprocess.run(cli + ["add-admin","--data-dir",str(folder)], env=env, cwd=root,
                                input="fixture@example.org\n"+password+"\n",
                                text=True, capture_output=True,timeout=60)
        if create.returncode:
            raise RuntimeError("Administrator creation failed: " + create.stderr.replace(password,"[redacted]"))
        backup = root/"first.db"
        restored = root/"restored"
        for args in (["backup",str(backup),"--data-dir",str(folder)],["restore",str(backup),"--data-dir",str(restored)]):
            subprocess.run(cli+args,env=env,cwd=root,check=True)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1",0))
            port = probe.getsockname()[1]
        child = subprocess.Popen(cli+["start","--data-dir",str(restored),"--no-browser","--port",str(port)],env=env,cwd=root,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        try:
            for _ in range(100):
                if child.poll() is not None:
                    raise RuntimeError("Packaged station failed to start: " + child.stderr.read())
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",timeout=1) as res:
                        if res.status==200:
                            break
                except OSError:
                    time.sleep(0.15)
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/admin/login",
                json.dumps({"email":"fixture@example.org","password":password}).encode(),{"Content-Type":"application/json"})
            with urllib.request.urlopen(req) as res:
                token = json.load(res)["access_token"]
            with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/admin/clinics",
                    headers={"Authorization":"Bearer "+token})) as res:
                assert json.load(res) == []
                assert res.headers["Cache-Control"]=="no-store"
            print("Extracted Windows runtime, initial provisioning, backup, restore and authenticated clinic access passed.")
        finally:
            child.terminate()
            child.wait(timeout=15)


if __name__ == "__main__":
    main()
