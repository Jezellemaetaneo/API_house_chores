# ==================================================
# HOUSE CHORES API (JSON + XML + CRUD)
# Flask + MySQL + JWT + Session
# ==================================================

from flask import Flask, request, jsonify, render_template_string, session
from flask_bcrypt import Bcrypt
from functools import wraps
import datetime
import jwt
import MySQLdb
import MySQLdb.cursors
import xml.etree.ElementTree as ET
import os

# ==================================================
# APP SETUP
# ==================================================
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "supersecretkey123"),
    JWT_EXP_HOURS=2
)

# ==================================================
# DATABASE CONFIG
# ==================================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "house_chores"
}

def get_db():
    return MySQLdb.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        passwd=DB_CONFIG["password"],
        db=DB_CONFIG["database"],
        cursorclass=MySQLdb.cursors.DictCursor,
        autocommit=False,
        charset="utf8mb4"
    )

# ==================================================
# DB INIT
# ==================================================
def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE,
        password VARCHAR(255)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS members (
        member_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) UNIQUE
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chores (
        chore_id INT AUTO_INCREMENT PRIMARY KEY,
        chore_name VARCHAR(100) UNIQUE,
        frequency VARCHAR(50)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chore_assignments (
        assignment_id INT AUTO_INCREMENT PRIMARY KEY,
        member_id INT,
        chore_id INT,
        assigned_date DATE,
        is_completed TINYINT(1),
        FOREIGN KEY (member_id) REFERENCES members(member_id),
        FOREIGN KEY (chore_id) REFERENCES chores(chore_id)
    )""")
    db.commit(); db.close()

# ==================================================
# XML + RESPONSE HELPER
# ==================================================
def to_xml(data, root_name="items"):
    root = ET.Element(root_name)
    if isinstance(data, dict):
        data = [data]
    for row in data:
        item = ET.SubElement(root, "item")
        for k, v in row.items():
            ET.SubElement(item, k).text = str(v)
    return ET.tostring(root, encoding="utf-8")

def respond(data, root="items", status=200):
    fmt = request.args.get("format", "").lower()
    accept = request.headers.get("Accept", "")
    if fmt == "xml" or "application/xml" in accept:
        return app.response_class(to_xml(data, root), mimetype="application/xml", status=status)
    return jsonify(data), status

# ==================================================
# JWT DECORATOR
# ==================================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
        else:
            token = session.get("token")
        if not token:
            return respond({"error": "Token missing"}, 401)
        try:
            jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except Exception:
            return respond({"error": "Invalid or expired token"}, 401)
        return f(*args, **kwargs)
    return decorated

# ==================================================
# AUTH ROUTES
# ==================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return """
        <h1>Register</h1>
        <form method="POST">
            <input name="username" required><br><br>
            <input name="password" type="password" required><br><br>
            <button>Register</button>
        </form>"""
    
    db = get_db(); cur = db.cursor()
    username = request.form["username"]
    password = bcrypt.generate_password_hash(request.form["password"]).decode()
    cur.execute("INSERT INTO users (username,password) VALUES (%s,%s)", (username, password))
    db.commit(); db.close()
    return "<h3>Registered</h3><a href='/login'>Login</a>"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return """
        <h1>Login</h1>
        <form method="POST">
            <input name="username" required><br><br>
            <input name="password" type="password" required><br><br>
            <button>Login</button>
        </form>"""
    
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM users WHERE username=%s", (request.form["username"],))
    user = cur.fetchone(); db.close()

    if not user or not bcrypt.check_password_hash(user["password"], request.form["password"]):
        return "<h3>Invalid credentials</h3>"

    token = jwt.encode({
        "user": user["username"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    session["token"] = token
    return "<h3>Login Success</h3><a href='/members'>View Members</a>"

# ==================================================
# MEMBERS CRUD PAGE
# ==================================================
@app.route("/members")
@token_required
def members_page():
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM members")
    members = cur.fetchall(); db.close()

    return render_template_string("""
<h1>Members</h1>
<a href="/members/add">➕ Add Member</a><hr>
{% for m in members %}
<p>
<b>{{ m.name }}</b>
<a href="/members/edit/{{ m.member_id }}">✏ Edit</a>
<form method="POST" action="/members/delete/{{ m.member_id }}" style="display:inline;">
<button onclick="return confirm('Delete member?')">🗑 Delete</button>
</form>
</p>
{% endfor %}
""", members=members)

@app.route("/members/add", methods=["GET", "POST"])
@token_required
def add_member():
    if request.method == "GET":
        return """
        <h2>Add Member</h2>
        <form method="POST">
            <input name="name" placeholder="Member name" required><br><br>
            <button>Add</button>
        </form>
        <a href="/members">Back</a>
        """
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO members (name) VALUES (%s)", (request.form["name"],))
    db.commit(); db.close()
    return "<h3>Member added</h3><a href='/members'>Back</a>"

@app.route("/members/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit_member(id):
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    if request.method == "GET":
        cur.execute("SELECT * FROM members WHERE member_id=%s", (id,))
        member = cur.fetchone(); db.close()
        return f"""
        <h2>Edit Member</h2>
        <form method="POST">
            <input name="name" value="{member['name']}" required><br><br>
            <button>Update</button>
        </form>
        <a href="/members">Back</a>
        """
    cur.execute("UPDATE members SET name=%s WHERE member_id=%s", (request.form["name"], id))
    db.commit(); db.close()
    return "<h3>Member updated</h3><a href='/members'>Back</a>"

@app.route("/members/delete/<int:id>", methods=["POST"])
@token_required
def delete_member(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM members WHERE member_id=%s", (id,))
    db.commit(); db.close()
    return "<h3>Member deleted</h3><a href='/members'>Back</a>"

# ==================================================
# TODO: Similar CRUD Pages for Chores & Assignments
# ==================================================

# ==================================================
# HOME
# ==================================================
@app.route("/")
def index():
    return """
    <h2>House Chores API</h2>
    <a href='/login'>Login</a> |
    <a href='/register'>Register</a>
    """

# ==================================================
# RUN APP
# ==================================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
