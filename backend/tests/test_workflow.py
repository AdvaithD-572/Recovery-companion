import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select


class RecoveryFlow(unittest.TestCase):
    def test_visit_report_and_clinic_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["DATABASE_URL"] = os.environ.get("RC_ISOLATED_TEST_DATABASE") or ("sqlite+aiosqlite:///" + (Path(folder) / "test.db").as_posix())
            os.environ["GEMINI_API_KEY"] = ""
            from app.main import app
            from app.core.database import AsyncSessionLocal
            from app.core.security import hash_password
            from app.models import Clinician
            from app.care import Staff
            from app.registry import Clinic
            from app.core.gemini import client
            from fastapi import HTTPException
            async def staff(email, clinic, role):
                async with AsyncSessionLocal.begin() as db:
                    if not await db.scalar(select(Clinic.id).where(Clinic.name == clinic)):
                        db.add(Clinic(name=clinic, scope=clinic))
                    row = Clinician(email=email,full_name=role,hashed_password=hash_password("synthetic-test-password"))
                    db.add(row)
                    await db.flush()
                    db.add(Staff(id=row.id,clinic=clinic,role=role))
            with TestClient(app) as http, patch("app.core.gemini.genai.Client") as provider:
                with self.assertRaises(HTTPException):
                    client()
                provider.assert_not_called()
                with patch("app.core.gemini.settings.GEMINI_API_KEY","unit-test-sentinel"), patch("app.core.gemini.genai.Client") as simulated:
                    self.assertIs(client(),simulated.return_value)
                def request(method,path,body=None,auth=None,want=200):
                    r=http.request(method,"/api/v1/"+path,json=body,headers=auth or {})
                    self.assertEqual(r.status_code,want,r.text)
                    return r.json() if r.content else None
                accounts=[]
                for i,(clinic,role) in enumerate([("Elm","clinician"),("Elm","receptionist"),("Pine","clinician")]):
                    email=f"user{i}@example.org"
                    http.portal.call(staff, email, clinic, role)
                    login=request("POST","auth/clinician/login",{"email":email,"password":"synthetic-test-password"})
                    accounts.append({"Authorization":"Bearer "+login["access_token"]})
                doc,desk,outsider=accounts
                email="patient@example.org"
                tokens=request("POST","auth/patient/register",{"email":email,"password":"synthetic-only","full_name":"Synthetic Patient"},want=201)
                patient={"Authorization":"Bearer "+tokens["access_token"]}
                pid=request("GET","patients/me",auth=patient)["id"]
                request("GET","patients/me",auth={"Authorization":"Bearer "+tokens["refresh_token"]},want=403)
                steps = [
                    {"dob":"1994-03-12", "height_cm":166, "weight_kg":60},
                    {"primary_condition":"Sample follow-up", "surgery_type":"Sample procedure",
                     "discharge_date":date.today().isoformat(), "allergies":["Synthetic allergen"]},
                    {"eating_habits":"Patient-entered notes"},
                    {"discharge_instructions":"Bring the diary to the visit",
                     "prescriptions":[{"drug_name":"Intake example","dosage":"Example dose",
                     "frequency":{"times":["09:30"]},"total_doses_bought":8,"start_date":date.today().isoformat()}]}]
                request('POST','patients/onboarding/step/1',{'dob':'invalid'},patient,422)
                request('POST','patients/onboarding/step/4',steps[-1],patient,422)
                for number, step in enumerate(steps, start=1):
                    request("POST", f"patients/onboarding/step/{number}", step, patient)
                request("POST", "patients/onboarding/step/4", steps[-1], patient)
                self.assertTrue(request("GET","patients/me",auth=patient)["onboarding_complete"])
                self.assertEqual(len(request("GET","prescriptions/",auth=patient)),1)
                token=request("POST","care/invitations",{"email":email},desk)
                request("POST","care/invitation/preview",token,patient)
                request("POST","care/link",token,patient)
                request("POST","care/link",token,patient,404)
                route="care/patients/"+pid
                self.assertEqual(request("GET","care/patients",auth=desk)["patients"][0]["id"],pid)
                request("POST",route+"/reports",{},outsider,404)
                rule={"event":"food","match":"fixture item","reason":"Synthetic rule solely for testing","severity":"Critical"}
                request("POST",route+"/rules",rule,desk,403)
                request("POST",route+"/rules",rule,doc)
                request("POST","food/log",{"meal_type":"lunch","food_items":[{"name":"Fixture Item"}]},patient,201)
                request("POST","logs/daily",{"log_date":date.today().isoformat(),"pain_score":3},patient,200)
                reaction={"event":"skipped","match":"sample A","reason":"Synthetic dose review","severity":"Needs review"}
                request("POST",route+"/rules",reaction,doc)
                rx=request("POST","prescriptions/",{"drug_name":"Sample A","dosage":"demo dose","frequency":{"times":["08:00"]},"total_doses_bought":5,"start_date":date.today().isoformat()},patient,201)
                stamp=datetime.now(timezone.utc).isoformat()
                dose={"id":str(uuid4()),"kind":"dose","occurred":stamp,"payload":{"prescription_id":rx["id"],"scheduled_time":stamp,"taken":False}}
                request("POST","care/sync",dose,patient)
                request("POST","care/sync",dose,patient)
                report=request("POST",route+"/reports",{},desk)
                self.assertEqual([e["status"] for e in report["report"]["events"] if e["type"]=="skipped"],["Needs review"])
                self.assertIn("Bring the diary to the visit", report["report"]["instructions"])
                self.assertEqual(report["report"]["height_cm"], 166)
                meal=next(row for row in report["report"]["events"] if row["type"]=="food")
                self.assertEqual(meal["status"],"Critical")
                visit={"text":"Follow-up completed","request_id":str(uuid4())}
                request("POST",route+"/visits",visit,desk,403)
                request("POST",route+"/visits",visit,patient,403)
                request("POST",route+"/visits",visit,doc)
                request("POST",route+"/visits",visit,doc)
                self.assertEqual(len(request("GET","care/me",auth=patient)["visits"]),1)
                self.assertEqual(request("GET","care/reports/"+report["id"],auth=desk),report)
                request("POST","care/reports/"+report["id"]+"/print",{},outsider,404)
                request("POST","care/reports/"+report["id"]+"/print",{},desk)
                request("POST","care/visits/"+visit["request_id"]+"/amendments",{"text":"Signed correction"},doc)
                late={"id":str(uuid4()),"kind":"meal","occurred":stamp,"payload":{"meal_type":"snack","food_items":[{"name":"Synthetic late meal"}]}}
                request("POST","care/sync",late,patient)
                refreshed=request("POST",route+"/reports",{},desk)
                request("POST","care/observations/food/"+meal["id"]+"/notes",{"text":"Clarified meal ingredient"},patient)
                with_note=request("POST",route+"/reports",{},desk)
                self.assertTrue(any("Clarified meal ingredient" in e["detail"] for e in with_note["report"]["events"]))
                self.assertEqual(request("GET","care/reports/"+report["id"],auth=desk),report)
                self.assertTrue(any(e["late"] and "Synthetic late meal" in e["detail"] for e in refreshed["report"]["events"]))
                self.assertFalse(any(e["type"]=="check-in" for e in refreshed["report"]["events"]))
                self.assertIn(report["id"],[r["id"] for r in request("GET",route+"/reports",auth=desk)])
                request("DELETE","care/link",auth=patient)
                request("GET","care/reports/"+report["id"],auth=desk,want=404)
                self.assertEqual(http.get("/clinic/").status_code,200)
                from app.registry import Administrator
                async def create_admin():
                    async with AsyncSessionLocal.begin() as db:
                        db.add(Administrator(email="admin@example.org", hashed_password=hash_password("local-test-admin")))
                http.portal.call(create_admin)
                admin_session = request("POST", "admin/login", {"email":"admin@example.org","password":"local-test-admin"})
                admin = {"Authorization":"Bearer " + admin_session["access_token"]}
                for unauthorized in (patient, doc, desk):
                    request("GET", "admin/patients", auth=unauthorized, want=403)
                    request("GET", "admin/patients/"+pid, auth=unauthorized, want=403)
                    request("POST", "admin/clinics", {"name":"West","staff_name":"Test doctor","staff_email":"west@example.org","staff_password":"synthetic-west"}, unauthorized,403)
                request("GET","care/patients",auth=admin,want=403)
                self.assertEqual(request("GET","admin/patients?q=synthetic",auth=admin)["patients"][0]["id"],pid)
                self.assertEqual(request("GET","admin/patients/"+pid,auth=admin)["height_cm"],166)
                new_clinic = {"name":"West","staff_name":"Test doctor","staff_email":"west@example.org","staff_password":"synthetic-west"}
                west = request("POST","admin/clinics",new_clinic,admin,201)
                request("POST","admin/clinics",new_clinic,admin,409)
                creds = {"email":"west@example.org","password":"synthetic-west"}
                west_session = request("POST","auth/clinician/login",creds)
                west_staff = {"Authorization":"Bearer " + west_session["access_token"]}
                invitation = request("POST","care/invitations",{"email":email},west_staff)
                pending = request("POST","care/invitations",{"email":email},west_staff)
                request("POST","care/link",invitation,patient)
                request("DELETE","admin/clinics/"+west["id"],auth=doc,want=403)
                request("DELETE","admin/clinics/"+west["id"],auth=admin,want=204)
                request("GET","care/patients",auth=west_staff,want=403)
                request("POST","auth/clinician/login",creds,want=401)
                request("POST","auth/refresh",{"refresh_token":west_session["refresh_token"]},want=401)
                request("POST","care/link",pending,patient,404)
                recreated = request("POST","admin/clinics",new_clinic,admin,201)
                self.assertNotEqual(west["id"],recreated["id"])
                request("GET","care/patients",auth=west_staff,want=403)
                self.assertIsNone(request("GET","admin/patients/"+pid,auth=admin)["clinic"])
                request("DELETE","patients/me",{"password":"incorrect"},patient,403)
                request("DELETE","patients/me",{"password":"synthetic-only"},admin,403)
                request("DELETE","patients/me",{"password":"synthetic-only"},patient,204)
                request("GET","patients/me",auth=patient,want=404)
                request("POST","auth/patient/login",{"email":email,"password":"synthetic-only"},want=401)
                request("POST","auth/refresh",{"refresh_token":tokens["refresh_token"]},want=401)
                request("GET","admin/patients/"+pid,auth=admin,want=404)
                self.assertEqual(request("GET","admin/patients?q=synthetic",auth=admin)["patients"],[])
                async def preserved():
                    from app.care import Entry
                    async with AsyncSessionLocal() as db:
                        return await db.get(Entry,report["id"]) is not None and await db.get(Entry,visit["request_id"]) is not None
                self.assertTrue(http.portal.call(preserved))
                request("POST","auth/patient/register",{"email":email,"password":"different-password","full_name":"New profile"},want=201)
                provider.assert_not_called()
