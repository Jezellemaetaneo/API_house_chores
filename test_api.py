import unittest
import json
from app import app

class HouseChoresAPITest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        self.creds = {"username": "testuser", "password": "testpass"}

        # Register user (ignore conflict)
        self.client.post("/auth/register", json=self.creds)

        # Login to get token
        login_res = self.client.post("/auth/login", json=self.creds)
        data = login_res.get_json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def test_members_crud(self):
        res = self.client.post("/members", headers=self.headers, json={"name": "John"})
        self.assertEqual(res.status_code, 201)

        res = self.client.get("/members", headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_chores_crud(self):
        res = self.client.post("/chores", headers=self.headers, json={"chore_name": "Wash dishes", "frequency": "Daily"})
        self.assertEqual(res.status_code, 201)

    def test_assignments_crud(self):
        member_res = self.client.post("/members", headers=self.headers, json={"name": "Alice"}).get_json()
        member_id = member_res["member_id"]

        chore_res = self.client.post("/chores", headers=self.headers, json={"chore_name": "Vacuum", "frequency": "Weekly"}).get_json()
        chore_id = chore_res["chore_id"]

        assign_res = self.client.post("/assignments", headers=self.headers, json={
            "member_id": member_id,
            "chore_id": chore_id,
            "assigned_date": "2025-12-13"
        })
        self.assertEqual(assign_res.status_code, 201)

if __name__ == "__main__":
    unittest.main()
