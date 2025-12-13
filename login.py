from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
import MySQLdb
import MySQLdb.cursors
import jwt
import datetime
from functools import wraps
import os

# =========================
# App setup
# =========================
app = Flask(__name__)
bcrypt = Bcrypt(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "supersecretkey123")
app.config["JWT_EXP_HOURS"] = 2

# =========================
# Database config
# =========================
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "root"
DB_NAME = "house_chores"

def get_db_connection():
    return MySQLdb.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        cursorclass=MySQLdb.cursors.DictCursor
    )

def get_cursor():
    conn = get_db_connection()
    return conn, conn.cursor()

# SAFE request data reader (JSON or form)
def get_request_data():
    return request.get_json(silent=True) or request.form or {}

# =========================
# JWT decorator
# =========================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"error": "token missing"}), 401
        try:
            token = auth.replace("Bearer ", "")
            jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

# =========================
# AUTH ROUTES
# =========================
@app.route("/auth/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return """
        <h2>Register</h2>
        <form method="post">
            <input name="username" placeholder="username"><br>
            <input name="password" type="password" placeholder="password"><br>
            <button>Register</button>
        </form>
        """, 200, {"Content-Type": "text/html"}

    data = get_request_data()
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    conn, cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return jsonify({"error": "username exists"}), 409

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s,%s)",
            (username, hashed)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "user registered"}), 201


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return """
        <h2>Login</h2>
        <form method="post">
            <input name="username"><br>
            <input name="password" type="password"><br>
            <button>Login</button>
        </form>
        """, 200, {"Content-Type": "text/html"}

    data = get_request_data()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    conn, cur = get_cursor()
    try:
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"error": "invalid credentials"}), 401

    token = jwt.encode(
        {
            "user": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return jsonify({"token": token})

# =========================
# MEMBERS
# =========================
@app.route("/members", methods=["GET", "POST"])
@token_required
def members():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM members")
            return jsonify(cur.fetchall())
        finally:
            cur.close()
            conn.close()

    data = get_request_data()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400

    conn, cur = get_cursor()
    try:
        cur.execute("INSERT INTO members (name) VALUES (%s)", (name,))
        conn.commit()
        return jsonify({"member_id": cur.lastrowid, "name": name}), 201
    finally:
        cur.close()
        conn.close()

# =========================
# CHORES
# =========================
@app.route("/chores", methods=["GET", "POST"])
@token_required
def chores():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM chores")
            return jsonify(cur.fetchall())
        finally:
            cur.close()
            conn.close()

    data = get_request_data()
    chore = data.get("chore_name")
    freq = data.get("frequency")

    if not chore or not freq:
        return jsonify({"error": "chore_name and frequency required"}), 400

    conn, cur = get_cursor()
    try:
        cur.execute(
            "INSERT INTO chores (chore_name, frequency) VALUES (%s,%s)",
            (chore, freq)
        )
        conn.commit()
        return jsonify({"chore_id": cur.lastrowid}), 201
    finally:
        cur.close()
        conn.close()

# =========================
# ASSIGNMENTS
# =========================
@app.route("/assignments", methods=["GET", "POST"])
@token_required
def assignments():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM chore_assignments")
            rows = cur.fetchall()
            for r in rows:
                if isinstance(r["assigned_date"], (datetime.date, datetime.datetime)):
                    r["assigned_date"] = r["assigned_date"].isoformat()
            return jsonify(rows)
        finally:
            cur.close()
            conn.close()

    data = get_request_data()
    member_id = data.get("member_id")
    chore_id = data.get("chore_id")
    assigned_date = data.get("assigned_date")

    if not member_id or not chore_id or not assigned_date:
        return jsonify({"error": "missing fields"}), 400

    conn, cur = get_cursor()
    try:
        cur.execute(
            """INSERT INTO chore_assignments
               (member_id, chore_id, assigned_date, is_completed)
               VALUES (%s,%s,%s,0)""",
            (member_id, chore_id, assigned_date)
        )
        conn.commit()
        return jsonify({"assignment_id": cur.lastrowid}), 201
    finally:
        cur.close()
        conn.close()

# =========================
# SEARCH
# =========================
@app.route("/api/search", methods=["GET"])
@token_required
def search():
    q = request.args.get("q", "")
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT * FROM chores WHERE chore_name LIKE %s", (f"%{q}%",))
        return jsonify(cur.fetchall())
    finally:
        cur.close()
        conn.close()

# =========================
# HEALTH CHECK
# =========================
@app.route("/")
def index():
    return jsonify({"status": "API running"})

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
