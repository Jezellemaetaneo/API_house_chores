from flask import Flask, request, jsonify, make_response, abort, g
from functools import wraps
from flask_bcrypt import Bcrypt
import datetime
import xmltodict
import re

# Ensure MySQLdb API on Windows
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    pass

import MySQLdb
import MySQLdb.cursors
import jwt

app = Flask(__name__)
bcrypt = Bcrypt(app)

# ----- Change these to your values -----
app.config["SECRET_KEY"] = "mysecretkey123"
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "root"
DB_NAME = "house_chores"
# ---------------------------------------

def _create_db_connection():
    return MySQLdb.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        cursorclass=MySQLdb.cursors.DictCursor,
        autocommit=False,
        charset='utf8mb4'
    )

db = _create_db_connection()

def get_cursor():
    global db
    try:
        # ping with reconnect True where supported
        try:
            db.ping(True)
        except TypeError:
            db.ping()
    except Exception:
        try:
            db.close()
        except Exception:
            pass
        db = _create_db_connection()
    return db.cursor()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth:
            return make_response(jsonify({"error": "Authorization header required"}), 401)
        m = re.match(r"^\s*Bearer\s+(.+)$", auth, re.I)
        if not m:
            return make_response(jsonify({"error": "Authorization header must be 'Bearer <token>'"}), 401)
        token = m.group(1)
        try:
            payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            g.current_user = payload.get("user")
        except jwt.ExpiredSignatureError:
            return make_response(jsonify({"error": "Token expired"}), 401)
        except Exception:
            return make_response(jsonify({"error": "Invalid token"}), 401)
        return f(*args, **kwargs)
    return decorated

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return make_response(jsonify({"error": "username and password required"}), 400)

    cur = get_cursor()
    try:
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
    finally:
        cur.close()

    if not user:
        return make_response(jsonify({"error": "invalid credentials"}), 401)

    if not bcrypt.check_password_hash(user["password"], password):
        return make_response(jsonify({"error": "invalid credentials"}), 401)

    token = jwt.encode(
        {
            "user": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return jsonify({"access_token": token})

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return make_response(jsonify({"error": "username and password required"}), 400)

    cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            return make_response(jsonify({"error": "username exists"}), 409)

        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
        db.commit()
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not create user"}), 500)
    finally:
        cur.close()

    return jsonify({"message": "user created"}), 201

def respond(data, status=200):
    fmt = request.args.get("format", "json").lower()
    if fmt == "xml":
        root = {"response": data} if isinstance(data, dict) else {"response": {"item": data}}
        xml_data = xmltodict.unparse(root, pretty=True)
        response = make_response(xml_data, status)
        response.headers["Content-Type"] = "application/xml"
        return response
    return make_response(jsonify(data), status)

# Members
@app.route('/members', methods=['GET'])
@token_required
def list_members():
    q = request.args.get('q')
    sql = "SELECT member_id, name FROM members"
    params = []
    if q:
        sql += " WHERE name LIKE %s"
        params.append(f"%{q}%")
    cur = get_cursor()
    try:
        cur.execute(sql, tuple(params))
        members = cur.fetchall()
    finally:
        cur.close()
    return respond({"members": members})

@app.route('/members', methods=['POST'])
@token_required
def create_member():
    payload = request.json or {}
    name = (payload.get('name') or "").strip()
    if not name:
        return make_response(jsonify({"error": "name required"}), 400)
    cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM members WHERE name = %s", (name,))
        if cur.fetchone():
            return make_response(jsonify({"error": "member exists"}), 409)
        cur.execute("INSERT INTO members (name) VALUES (%s)", (name,))
        db.commit()
        new_id = cur.lastrowid
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not create member"}), 500)
    finally:
        cur.close()
    return respond({"member_id": new_id, "name": name}, 201)

@app.route('/members/<int:member_id>', methods=['PUT'])
@token_required
def update_member(member_id):
    payload = request.json or {}
    name = (payload.get('name') or "").strip()
    if not name:
        return make_response(jsonify({"error": "name required"}), 400)
    cur = get_cursor()
    try:
        cur.execute("UPDATE members SET name = %s WHERE member_id = %s", (name, member_id))
        if cur.rowcount == 0:
            return make_response(jsonify({"error": "member not found"}), 404)
        db.commit()
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not update member"}), 500)
    finally:
        cur.close()
    return respond({"member_id": member_id, "name": name})

@app.route('/members/<int:member_id>', methods=['DELETE'])
@token_required
def delete_member(member_id):
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM members WHERE member_id = %s", (member_id,))
        if cur.rowcount == 0:
            return make_response(jsonify({"error": "member not found"}), 404)
        db.commit()
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not delete member"}), 500)
    finally:
        cur.close()
    return '', 204

# Chores
@app.route('/chores', methods=['GET'])
@token_required
def list_chores():
    q = request.args.get('q')
    sql = "SELECT chore_id, chore_name, frequency FROM chores"
    params = []
    if q:
        sql += " WHERE chore_name LIKE %s"
        params.append(f"%{q}%")
    cur = get_cursor()
    try:
        cur.execute(sql, tuple(params))
        chores = cur.fetchall()
    finally:
        cur.close()
    return respond({"chores": chores})

@app.route('/chores', methods=['POST'])
@token_required
def create_chore():
    payload = request.json or {}
    chore_name = (payload.get('chore_name') or "").strip()
    frequency = (payload.get('frequency') or "").strip()
    if not chore_name or not frequency:
        return make_response(jsonify({"error": "chore_name and frequency required"}), 400)
    cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM chores WHERE chore_name = %s", (chore_name,))
        if cur.fetchone():
            return make_response(jsonify({"error": "chore exists"}), 409)
        cur.execute("INSERT INTO chores (chore_name, frequency) VALUES (%s, %s)", (chore_name, frequency))
        db.commit()
        new_id = cur.lastrowid
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not create chore"}), 500)
    finally:
        cur.close()
    return respond({"chore_id": new_id, "chore_name": chore_name}, 201)

@app.route('/chores/<int:chore_id>', methods=['PUT'])
@token_required
def update_chore(chore_id):
    payload = request.json or {}
    chore_name = (payload.get('chore_name') or "").strip()
    frequency = (payload.get('frequency') or "").strip()
    if not chore_name or not frequency:
        return make_response(jsonify({"error": "chore_name and frequency required"}), 400)
    cur = get_cursor()
    try:
        cur.execute("UPDATE chores SET chore_name=%s, frequency=%s WHERE chore_id=%s", (chore_name, frequency, chore_id))
        if cur.rowcount == 0:
            return make_response(jsonify({"error": "chore not found"}), 404)
        db.commit()
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not update chore"}), 500)
    finally:
        cur.close()
    return respond({"chore_id": chore_id, "chore_name": chore_name})

@app.route('/chores/<int:chore_id>', methods=['DELETE'])
@token_required
def delete_chore(chore_id):
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM chores WHERE chore_id = %s", (chore_id,))
        if cur.rowcount == 0:
            return make_response(jsonify({"error": "chore not found"}), 404)
        db.commit()
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not delete chore"}), 500)
    finally:
        cur.close()
    return '', 204

# Assignments
@app.route('/assignments', methods=['GET'])
@token_required
def list_assignments():
    q_member = request.args.get('member_id', type=int)
    q_chore = request.args.get('chore_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    completed = request.args.get('completed')  # 'true' / 'false'

    sql = """SELECT assignment_id, member_id, chore_id, assigned_date, is_completed
             FROM chore_assignments WHERE 1=1"""
    params = []

    if q_member:
        sql += " AND member_id = %s"
        params.append(q_member)
    if q_chore:
        sql += " AND chore_id = %s"
        params.append(q_chore)
    if date_from:
        sql += " AND assigned_date >= %s"
        params.append(date_from)
    if date_to:
        sql += " AND assigned_date <= %s"
        params.append(date_to)
    if completed is not None:
        val = 1 if completed.lower() in ("1", "true", "yes") else 0
        sql += " AND is_completed = %s"
        params.append(val)

    cur = get_cursor()
    try:
        cur.execute(sql, tuple(params))
        results = cur.fetchall()
    finally:
        cur.close()
    return respond({"assignments": results})

@app.route('/assignments', methods=['POST'])
@token_required
def create_assignment():
    payload = request.json or {}
    member_id = payload.get('member_id')
    chore_id = payload.get('chore_id')
    assigned_date = payload.get('assigned_date')
    is_completed = bool(payload.get('is_completed', False))

    if not member_id or not chore_id or not assigned_date:
        return make_response(jsonify({"error": "member_id, chore_id and assigned_date required"}), 400)

    # validate FK existence
    cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM members WHERE member_id = %s", (member_id,))
        if not cur.fetchone():
            return make_response(jsonify({"error": "member not found"}), 404)
        cur.execute("SELECT 1 FROM chores WHERE chore_id = %s", (chore_id,))
        if not cur.fetchone():
            return make_response(jsonify({"error": "chore not found"}), 404)
    finally:
        cur.close()

    # validate date format (expect ISO YYYY-MM-DD)
    try:
        datetime.date.fromisoformat(assigned_date)
    except Exception:
        return make_response(jsonify({"error": "assigned_date must be YYYY-MM-DD"}), 400)

    cur = get_cursor()
    try:
        cur.execute(
            "INSERT INTO chore_assignments (member_id, chore_id, assigned_date, is_completed) VALUES (%s, %s, %s, %s)",
            (member_id, chore_id, assigned_date, 1 if is_completed else 0)
        )
        db.commit()
        new_id = cur.lastrowid
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not create assignment"}), 500)
    finally:
        cur.close()

    return respond({"assignment_id": new_id}, 201)

@app.route('/assignments/<int:assignment_id>', methods=['PUT'])
@token_required
def update_assignment(assignment_id):
    payload = request.json or {}

    # ensure assignment exists
    cur = get_cursor()
    try:
        cur.execute("SELECT 1 FROM chore_assignments WHERE assignment_id = %s", (assignment_id,))
        if not cur.fetchone():
            return make_response(jsonify({"error": "assignment not found"}), 404)
    finally:
        cur.close()

    fields = []
    params = []
    if 'member_id' in payload:
        fields.append("member_id = %s")
        params.append(payload.get('member_id'))
    if 'chore_id' in payload:
        fields.append("chore_id = %s")
        params.append(payload.get('chore_id'))
    if 'assigned_date' in payload:
        try:
            datetime.date.fromisoformat(payload.get('assigned_date'))
        except Exception:
            return make_response(jsonify({"error": "assigned_date must be YYYY-MM-DD"}), 400)
        fields.append("assigned_date = %s")
        params.append(payload.get('assigned_date'))
    if 'is_completed' in payload:
        fields.append("is_completed = %s")
        params.append(1 if payload.get('is_completed') else 0)

    if not fields:
        return make_response(jsonify({"error": "no fields to update"}), 400)

    params.append(assignment_id)
    sql = f"UPDATE chore_assignments SET {', '.join(fields)} WHERE assignment_id = %s"

    cur = get_cursor()
    try:
        cur.execute(sql, tuple(params))
        if cur.rowcount == 0:
            return make_response(jsonify({"error": "assignment not found"}), 404)
        db.commit()
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not update assignment"}), 500)
    finally:
        cur.close()

    return respond({"assignment_id": assignment_id})

@app.route('/assignments/<int:assignment_id>', methods=['DELETE'])
@token_required
def delete_assignment(assignment_id):
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM chore_assignments WHERE assignment_id = %s", (assignment_id,))
        if cur.rowcount == 0:
            return make_response(jsonify({"error": "assignment not found"}), 404)
        db.commit()
    except Exception:
        db.rollback()
        return make_response(jsonify({"error": "could not delete assignment"}), 500)
    finally:
        cur.close()
    return '', 204

@app.route('/', methods=['GET'])
def hello():
    return jsonify({"msg":"Chore API up. Use /auth/login to get token."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)