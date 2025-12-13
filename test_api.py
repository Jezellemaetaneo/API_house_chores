import unittest
import requests

BASE_URL = "http://127.0.0.1:5000"

class TestHouseChoresAPI(unittest.TestCase):

    def setUp(self):
        # Create a test user
        self.username = "testuser"
        self.password = "testpass"
        r = requests.post(f"{BASE_URL}/auth/register", json={
            "username": self.username,
            "password": self.password
        })
        # Login to get token
        r = requests.post(f"{BASE_URL}/auth/login", json={
            "username": self.username,
            "password": self.password
        })
        data = r.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def test_members_crud(self):
        # Create member
        r = requests.post(f"{BASE_URL}/members", json={"name": "Alice"}, headers=self.headers)
        self.assertIn(r.status_code, [201, 409])

        # Get members
        r = requests.get(f"{BASE_URL}/members", headers=self.headers)
        self.assertEqual(r.status_code, 200)

    def test_chores_crud(self):
        # Create chore
        r = requests.post(f"{BASE_URL}/chores", json={"chore_name": "Wash dishes", "frequency": "Daily"}, headers=self.headers)
        self.assertIn(r.status_code, [201, 409])

        # Search chores
        r = requests.get(f"{BASE_URL}/api/search?q=Wash", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json().get("results"), list)

    def test_search(self):
        r = requests.get(f"{BASE_URL}/api/search?q=Nonexistent", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])

if __name__ == "__main__":
    unittest.main()
