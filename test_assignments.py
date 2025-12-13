import unittest
import json
from app import app, get_cursor

class AssignmentsAPITest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # Create a test member and chore
        conn, cur = get_cursor()
        cur.execute("INSERT INTO members (name) VALUES ('Test Member')")
        self.member_id = cur.lastrowid
        cur.execute("INSERT INTO chores (chore_name, frequency) VALUES ('Test Chore','daily')")
        self.chore_id = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()

    def test_create_assignment(self):
        res = self.client.post("/assignments", json={
            "member_id": self.member_id,
            "chore_id": self.chore_id,
            "assigned_date": "2025-12-13",
            "is_completed": False
        })
        data = res.get_json()
        self.assertEqual(res.status_code, 201)
        self.assertIn("assignment_id", data)

    def test_get_assignments(self):
        res = self.client.get("/assignments")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("assignments", data)

    def test_update_assignment(self):
        # Create first
        res = self.client.post("/assignments", json={
            "member_id": self.member_id,
            "chore_id": self.chore_id,
            "assigned_date": "2025-12-13",
            "is_completed": False
        })
        assignment_id = res.get_json()["assignment_id"]

        res2 = self.client.put(f"/assignments/{assignment_id}", json={
            "is_completed": True
        })
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["assignment_id"], assignment_id)

    def test_delete_assignment(self):
        # Create first
        res = self.client.post("/assignments", json={
            "member_id": self.member_id,
            "chore_id": self.chore_id,
            "assigned_date": "2025-12-13",
            "is_completed": False
        })
        assignment_id = res.get_json()["assignment_id"]

        res2 = self.client.delete(f"/assignments/{assignment_id}")
        self.assertEqual(res2.status_code, 204)

if __name__ == "__main__":
    unittest.main()
