# API_house_chores
# Chore REST API (CSE1 Final Project)

## What
A Flask CRUD REST API backed by MySQL for managing house chores and assignments. Supports JSON and XML outputs, JWT-based auth, search, and tests with pytest.

## Setup (local)
1. Install MySQL and create a database (or use the provided `schema.sql`).
2. Clone repo.
3. Copy `.env.example` to `.env` and edit DB credentials.
4. Create and activate a virtualenv (do not commit it).
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
