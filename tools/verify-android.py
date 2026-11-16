"""Test the installed APK on an unlocked test emulator at its signed-out screen."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import threading
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = os.environ.get("ADB", "adb")
DEVICE = os.environ.get("RC_EMULATOR", "emulator-5554")
PACKAGE = os.environ.get("RC_ANDROID_PACKAGE", "com.example.recovery_companion.patient")
ACTIVITY = PACKAGE + "/com.example.recovery_companion.MainActivity"


def adb(*args):
    return subprocess.check_output([ADB, "-s", DEVICE, *args], timeout=30)


def controls():
    for _ in range(5):
        result = adb("shell", "uiautomator", "dump", "/sdcard/rc-test-window.xml")
        if b"dumped to" in result:
            xml = adb("shell", "cat", "/sdcard/rc-test-window.xml")
            return list(ET.fromstring(xml).iter("node"))
        time.sleep(1)
    raise RuntimeError("Android has no accessibility window ready.")


def find(label="", field=None):
    for attempt in range(5):
        nodes = controls()
        if field is not None:
            matches = [n for n in nodes if n.get("class") == "android.widget.EditText"]
            if len(matches) > field:
                return matches[field]
        else:
            for n in nodes:
                if label in (n.get("content-desc") or "").splitlines() or label == n.get("text"):
                    return n
        time.sleep(1)
    visible = [n.get("content-desc") for n in nodes if n.get("content-desc") and n.get("password") != "true"]
    raise RuntimeError(f"Missing control {label!r} (field {field}). Visible: {visible}")


def tap(node):
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds")))
    adb("shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2))


def request(path, body=None, token=None):
    headers = {"Content-Type":"application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1/" + path, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.load(res)


def main():
    if not DEVICE.startswith("emulator-"):
        raise ValueError("Select a test emulator.")
    with subprocess.Popen([sys.executable, "-u", "demo.py"], cwd=os.environ.get("RC_BACKEND",ROOT/"backend"),
                          stdout=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL) as demo:
        try:
            for line in demo.stdout:
                if line.startswith("Temporary demo password: "):
                    password = line.split()[-1]
                    break
            else:
                raise RuntimeError("Demo did not start")
            # Uvicorn writes access logs to the same pipe as the startup credentials.
            # Keep draining it while we exercise the device so a full pipe cannot stall HTTP.
            threading.Thread(target=demo.stdout.read, daemon=True).start()
            adb("shell","am","start","-n",ACTIVITY)
            find("Welcome back")
            tap(find(field=0))
            time.sleep(2)
            adb("shell","input","keycombination","113","29")
            adb("shell","input","keyevent","67")
            adb("shell","input","text","patient@example.org")
            email = find(field=0)
            if "patient@example.org" not in email.get("text", ""):
                raise RuntimeError("The emulator keyboard did not enter the full synthetic email.")
            tap(find(field=1))
            time.sleep(1.5)
            adb("shell","input","keycombination","113","29")
            adb("shell","input","keyevent","67")
            adb("shell","input","text",password)
            adb("shell","input","keyevent","4")
            tap(find("Sign in"))
            find("Care record and attention tracker")
            (ROOT/"docs/demo/patient-home.png").write_bytes(adb("exec-out","screencap","-p"))
            tap(find("Food"))
            if os.environ.get("RC_TEST_OFFLINE"):
                adb("shell","cmd","connectivity","airplane-mode","enable")
                time.sleep(2)
            tap(find("Enter meal"))
            tap(find(field=0))
            time.sleep(1)
            adb("shell","input","text","EmulatorMeal")
            if "EmulatorMeal" not in find(field=0).get("text", ""):
                raise RuntimeError("The emulator did not enter the complete test meal.")
            adb("shell","input","keyevent","4")
            tap(find("Review"))
            tap(find("Save meal"))
            if os.environ.get("RC_TEST_OFFLINE"):
                time.sleep(2)
                adb("shell","am","force-stop",PACKAGE)
                adb("shell","am","start","-n",ACTIVITY)
                find("Care record and attention tracker")
                # User-visible pending state proves the write outlived the process.
                find("1 entries pending sync")
                adb("shell","cmd","connectivity","airplane-mode","disable")
                for _ in range(45):
                    if b"10.0.2.0" in adb("shell","ip","route"):
                        break
                    time.sleep(1)
                # Leave Today open so its periodic replay runs without a manual retry.
            staff = request("auth/clinician/login", {"email":"doctor@example.org", "password":password})["access_token"]
            pid = request("care/patients", token=staff)["patients"][0]["id"]
            for attempt in range(75):
                report = request(f"care/patients/{pid}/reports", {}, staff)["report"]
                if sum("EmulatorMeal" in row["detail"] for row in report["events"]) == 1:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Meal did not reach the report. Synthetic food entries: " +
                                   repr([e["detail"] for e in report["events"] if e["type"] == "food"]))
            tap(find("Records"))
            find("Attention tracker")
            if os.environ.get("RC_TEST_CLINIC_BROWSER"):
                subprocess.run(["node", str(ROOT/"tools/verify-clinic.cjs"), "--android-return"],
                               input=password+"\n", text=True, check=True, timeout=90)
                tap(find("Today"))
                find("Care record and attention tracker")
                tap(find("Records"))
                find("Refresh care record")
                # Scroll the patient journal using the actual test emulator's viewport.
                bounds = list(map(int, re.findall(r"\d+", find("Records").get("bounds"))))
                x, bottom = bounds[2] // 2, bounds[1]
                for _ in range(20):
                    if any("Emulator follow-up reviewed" in (n.get("content-desc") or "").splitlines()
                           for n in controls()):
                        break
                    adb("shell", "input", "swipe", str(x), str(bottom-30), str(x), str(bottom//3), "300")
                else:
                    raise RuntimeError("The clinic's new checkup did not appear after reopening Records.")
                print("Verified Android meal in clinic browser and finalized clinic note back on Android.")
            print("Verified Android patient sign-in, meal review/save, clinic report receipt and Records tab.")
        finally:
            if os.environ.get("RC_TEST_OFFLINE"):
                adb("shell","cmd","connectivity","airplane-mode","disable")
            demo.terminate()


if __name__ == "__main__":
    main()
