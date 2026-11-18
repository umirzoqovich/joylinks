import sys
import os
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from fastapi.testclient import TestClient
from main import app

class TestJoylinksCRM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def setUp(self):
        self.client = TestClient(app)

    def test_database_settings(self):
        database.set_setting("TEST_KEY", "TEST_VALUE")
        val = database.get_setting("TEST_KEY")
        self.assertEqual(val, "TEST_VALUE")

    def test_create_and_retrieve_lead(self):
        lead = database.create_lead(
            full_name="Test O'quvchi",
            phone="+998909998877",
            course="Ingliz tili (IELTS)",
            source="Test Suite",
            notes="Sinov lidi"
        )
        self.assertIsNotNone(lead)
        self.assertEqual(lead["full_name"], "Test O'quvchi")
        self.assertEqual(lead["status"], "NEW")

        # Update status
        updated = database.update_lead_status(lead["id"], "CONTACTED", changed_by="Tester")
        self.assertEqual(updated["status"], "CONTACTED")

        # Duplicate detection (re-apply)
        lead2 = database.create_lead(
            full_name="Test O'quvchi",
            phone="+998909998877",
            course="Nemis tili"
        )
        self.assertTrue(lead2.get("is_reapplied"))
        self.assertEqual(lead2["id"], lead["id"])

        # Clean up
        database.delete_lead(lead["id"])

    def test_web_routes(self):
        # 1. Homepage
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Joylinks", resp.text)

        # 2. Public Target Form
        resp_form = self.client.get("/form?course=IELTS&ref=Insta")
        self.assertEqual(resp_form.status_code, 200)
        self.assertIn("Joylinks", resp_form.text)

        # 3. Create lead via API
        payload = {
            "full_name": "API Test Foydalanuvchi",
            "phone": "+998911112233",
            "course": "IT va Dasturlash",
            "source": "Unit Test",
            "ad_name": "Target Test",
            "notes": "Avtotest"
        }
        res_create = self.client.post("/api/leads", json=payload)
        self.assertEqual(res_create.status_code, 200)
        data = res_create.json()
        self.assertEqual(data["status"], "ok")
        lead_id = data["lead"]["id"]

        # 4. List leads API
        res_list = self.client.get("/api/leads")
        self.assertEqual(res_list.status_code, 200)
        leads = res_list.json()
        self.assertTrue(any(l["id"] == lead_id for l in leads))

        # 5. Settings API
        res_settings = self.client.get("/api/settings")
        self.assertEqual(res_settings.status_code, 200)

        # 6. Export Excel
        res_excel = self.client.get("/export/excel")
        self.assertEqual(res_excel.status_code, 200)
        self.assertTrue(len(res_excel.content) > 0)

        # Clean up
        self.client.delete(f"/api/leads/{lead_id}")

if __name__ == "__main__":
    unittest.main()
