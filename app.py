from flask import Flask, request, jsonify, make_response
from flask_bcrypt import Bcrypt
import MySQLdb
import MySQLdb.cursors
import datetime
import xmltodict
import os

# ---------------------------
# App setup
# ---------------------------
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "supersecretkey123")

# ---------------------------
# Database connection
# ---------------------------
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
        cursorclass=MySQLdb.cursors.DictCursor,
        autocommit=False,
        charset="utf8mb4"
    )

def get_cursor():
    conn = get_db_connection()
    return conn, conn.cursor()

# ---------------------------
# Helper: XML/JSON response
# ---------------------------
def respond(data, status=200):
    fmt = request.args.get("format", "json").lower()
    if fmt == "xml":
        xml_data = xmltodict.unparse({"response": {"item": data}}, pretty=True)
        response = make_response(xml_data, status)
        response.headers["Content-Type"] = "application/xml"
        return response
    return make_response(jsonify(data), status)

# ---------------------------
# Auth routes (no token)
# ---------------------------
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    conn, cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return jsonify({"error": "username already exists"}), 409
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return jsonify({"message": "user created"}), 201

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json or {}
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
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": f"User {username} logged in successfully"})

# ---------------------------
# Members CRUD
# ---------------------------
@app.route("/members", methods=["GET", "POST"])
def members_collection():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT member_id, name FROM members")
            members = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        return respond({"members": members})
    
    elif request.method == "POST":
        payload = request.json or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"msg":"member name required"}), 400
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT 1 FROM members WHERE name=%s", (name,))
            if cur.fetchone():
                return jsonify({"msg":"member already exists"}), 409
            cur.execute("INSERT INTO members (name) VALUES (%s)", (name,))
            conn.commit()
            new_id = cur.lastrowid
        finally:
            cur.close()
            conn.close()
        return respond({"member_id": new_id, "name": name}, 201)

@app.route("/members/<int:member_id>", methods=["GET", "PUT", "DELETE"])
def member_detail(member_id):
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT member_id, name FROM members WHERE member_id=%s", (member_id,))
            member = cur.fetchone()
            if not member:
                return jsonify({"msg":"member not found"}), 404
        finally:
            cur.close()
            conn.close()
        return respond(member)

    elif request.method == "PUT":
        payload = request.json or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"msg":"member name required"}), 400
        conn, cur = get_cursor()
        try:
            cur.execute("UPDATE members SET name=%s WHERE member_id=%s", (name, member_id))
            if cur.rowcount == 0:
                return jsonify({"msg":"member not found"}), 404
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return respond({"member_id": member_id, "name": name})

    elif request.method == "DELETE":
        conn, cur = get_cursor()
        try:
            cur.execute("DELETE FROM members WHERE member_id=%s", (member_id,))
            if cur.rowcount == 0:
                return jsonify({"msg":"member not found"}), 404
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return '', 204

# ---------------------------
# Chores CRUD
# ---------------------------
@app.route("/chores", methods=["GET", "POST"])
def chores_collection():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT chore_id, chore_name, frequency FROM chores")
            chores = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        return respond({"chores": chores})
    
    elif request.method == "POST":
        payload = request.json or {}
        chore_name = (payload.get("chore_name") or "").strip()
        frequency = (payload.get("frequency") or "").strip()
        if not chore_name or not frequency:
            return jsonify({"msg":"chore_name and frequency required"}), 400
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT 1 FROM chores WHERE chore_name=%s", (chore_name,))
            if cur.fetchone():
                return jsonify({"msg":"chore already exists"}), 409
            cur.execute("INSERT INTO chores (chore_name, frequency) VALUES (%s,%s)", (chore_name, frequency))
            conn.commit()
            new_id = cur.lastrowid
        finally:
            cur.close()
            conn.close()
        return respond({"chore_id": new_id, "chore_name": chore_name}, 201)

@app.route("/chores/<int:chore_id>", methods=["GET", "PUT", "DELETE"])
def chore_detail(chore_id):
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM chores WHERE chore_id=%s", (chore_id,))
            chore = cur.fetchone()
            if not chore:
                return jsonify({"msg":"chore not found"}), 404
        finally:
            cur.close()
            conn.close()
        return respond(chore)

    elif request.method == "PUT":
        payload = request.json or {}
        chore_name = (payload.get("chore_name") or "").strip()
        frequency = (payload.get("frequency") or "").strip()
        if not chore_name or not frequency:
            return jsonify({"msg":"chore_name and frequency required"}), 400
        conn, cur = get_cursor()
        try:
            cur.execute("UPDATE chores SET chore_name=%s, frequency=%s WHERE chore_id=%s",
                        (chore_name, frequency, chore_id))
            if cur.rowcount == 0:
                return jsonify({"msg":"chore not found"}), 404
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return respond({"chore_id": chore_id, "chore_name": chore_name})

    elif request.method == "DELETE":
        conn, cur = get_cursor()
        try:
            cur.execute("DELETE FROM chores WHERE chore_id=%s", (chore_id,))
            if cur.rowcount == 0:
                return jsonify({"msg":"chore not found"}), 404
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return '', 204

# ---------------------------
# Assignments CRUD
# ---------------------------
@app.route("/assignments", methods=["GET", "POST"])
def assignments_collection():
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM chore_assignments")
            results = cur.fetchall()
            for r in results:
                if isinstance(r.get("assigned_date"), (datetime.date, datetime.datetime)):
                    r["assigned_date"] = r["assigned_date"].isoformat()
                r["is_completed"] = bool(r.get("is_completed"))
        finally:
            cur.close()
            conn.close()
        return respond({"assignments": results})

    elif request.method == "POST":
        payload = request.json or {}
        member_id = payload.get("member_id")
        chore_id = payload.get("chore_id")
        assigned_date = payload.get("assigned_date")
        is_completed = bool(payload.get("is_completed", False))

        if not member_id or not chore_id or not assigned_date:
            return jsonify({"msg":"member_id, chore_id, assigned_date required"}), 400

        try:
            datetime.date.fromisoformat(assigned_date)
        except Exception:
            return jsonify({"msg":"assigned_date must be ISO format YYYY-MM-DD"}), 400

        conn, cur = get_cursor()
        try:
            cur.execute(
                "INSERT INTO chore_assignments (member_id,chore_id,assigned_date,is_completed) VALUES (%s,%s,%s,%s)",
                (member_id, chore_id, assigned_date, int(is_completed))
            )
            conn.commit()
            new_id = cur.lastrowid
        finally:
            cur.close()
            conn.close()
        return respond({"assignment_id": new_id}, 201)

@app.route("/assignments/<int:assignment_id>", methods=["GET", "PUT", "DELETE"])
def assignment_detail(assignment_id):
    if request.method == "GET":
        conn, cur = get_cursor()
        try:
            cur.execute("SELECT * FROM chore_assignments WHERE assignment_id=%s", (assignment_id,))
            assignment = cur.fetchone()
            if not assignment:
                return jsonify({"msg":"assignment not found"}), 404
            if isinstance(assignment.get("assigned_date"), (datetime.date, datetime.datetime)):
                assignment["assigned_date"] = assignment["assigned_date"].isoformat()
            assignment["is_completed"] = bool(assignment.get("is_completed"))
        finally:
            cur.close()
            conn.close()
        return respond(assignment)

    elif request.method == "PUT":
        payload = request.json or {}
        fields, params = [], []
        if "member_id" in payload: fields.append("member_id=%s"); params.append(payload["member_id"])
        if "chore_id" in payload: fields.append("chore_id=%s"); params.append(payload["chore_id"])
        if "assigned_date" in payload:
            try:
                datetime.date.fromisoformat(payload["assigned_date"])
            except Exception:
                return jsonify({"msg":"assigned_date must be ISO format YYYY-MM-DD"}), 400
            fields.append("assigned_date=%s"); params.append(payload["assigned_date"])
        if "is_completed" in payload: fields.append("is_completed=%s"); params.append(int(bool(payload["is_completed"])))

        if not fields:
            return respond({"assignment_id": assignment_id})

        params.append(assignment_id)
        sql = f"UPDATE chore_assignments SET {', '.join(fields)} WHERE assignment_id=%s"

        conn, cur = get_cursor()
        try:
            cur.execute(sql, tuple(params))
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return respond({"assignment_id": assignment_id})

    elif request.method == "DELETE":
        conn, cur = get_cursor()
        try:
            cur.execute("DELETE FROM chore_assignments WHERE assignment_id=%s", (assignment_id,))
            if cur.rowcount == 0:
                return jsonify({"msg":"assignment not found"}), 404
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return '', 204

# ---------------------------
# Search chores
# ---------------------------
# ---------------------------
# Search chores (fixed)
# ---------------------------
@app.route("/api/search", methods=["GET", "POST"])
def search():
    # Determine query string
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        q = data.get("q", "").strip()
    else:
        q = (request.args.get("q") or "").strip()

    if not q:
        return jsonify({"msg": "query parameter 'q' is required"}), 400

    conn, cur = get_cursor()
    try:
        # Use parameterized query to prevent SQL injection
        cur.execute("SELECT chore_id, chore_name, frequency FROM chores WHERE chore_name LIKE %s", (f"%{q}%",))
        results = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return jsonify({"results": results})


# ---------------------------
# Health check
# ---------------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"msg":"Chore API up and running. No token required."})

# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)