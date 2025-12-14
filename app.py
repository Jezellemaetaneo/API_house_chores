# ==================================================
# HOUSE CHORES API (JSON + XML + CRUD + SEARCH)
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
# MEMBERS CRUD + SEARCH
# ==================================================
@app.route("/members")
@token_required
def members_page():
    keyword = request.args.get("search", "")
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    if keyword:
        cur.execute("SELECT * FROM members WHERE name LIKE %s", (f"%{keyword}%",))
    else:
        cur.execute("SELECT * FROM members")
    members = cur.fetchall(); db.close()
    
    return render_template_string("""
<h1>Members</h1>
<form method="GET">
    <input name="search" placeholder="Search members" value="{{ request.args.get('search', '') }}">
    <button>Search</button>
    <a href="/members">Reset</a>
</form>
<a href="/members/add">➕ Add Member</a> | <a href="/chores">Chores</a> | <a href="/assignments">Assignments</a>
<hr>
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
# CHORES CRUD + SEARCH
# ==================================================
@app.route("/chores")
@token_required
def chores_page():
    keyword = request.args.get("search", "")
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    if keyword:
        cur.execute("SELECT * FROM chores WHERE chore_name LIKE %s", (f"%{keyword}%",))
    else:
        cur.execute("SELECT * FROM chores")
    chores = cur.fetchall(); db.close()

    return render_template_string("""
<h1>Chores</h1>
<form method="GET">
    <input name="search" placeholder="Search chores" value="{{ request.args.get('search', '') }}">
    <button>Search</button>
    <a href="/chores">Reset</a>
</form>
<a href="/chores/add">➕ Add Chore</a> | <a href="/members">Members</a> | <a href="/assignments">Assignments</a>
<hr>
{% for c in chores %}
<p>
<b>{{ c.chore_name }}</b> - {{ c.frequency }}
<a href="/chores/edit/{{ c.chore_id }}">✏ Edit</a>
<form method="POST" action="/chores/delete/{{ c.chore_id }}" style="display:inline;">
<button onclick="return confirm('Delete chore?')">🗑 Delete</button>
</form>
</p>
{% endfor %}
""", chores=chores)

@app.route("/chores/add", methods=["GET", "POST"])
@token_required
def add_chore():
    if request.method == "GET":
        return """
        <h2>Add Chore</h2>
        <form method="POST">
            <input name="chore_name" placeholder="Chore name" required><br><br>
            <input name="frequency" placeholder="Frequency (e.g., Daily)" required><br><br>
            <button>Add</button>
        </form>
        <a href="/chores">Back</a>
        """
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO chores (chore_name, frequency) VALUES (%s,%s)",
                (request.form["chore_name"], request.form["frequency"]))
    db.commit(); db.close()
    return "<h3>Chore added</h3><a href='/chores'>Back</a>"

@app.route("/chores/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit_chore(id):
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    if request.method == "GET":
        cur.execute("SELECT * FROM chores WHERE chore_id=%s", (id,))
        chore = cur.fetchone(); db.close()
        return f"""
        <h2>Edit Chore</h2>
        <form method="POST">
            <input name="chore_name" value="{chore['chore_name']}" required><br><br>
            <input name="frequency" value="{chore['frequency']}" required><br><br>
            <button>Update</button>
        </form>
        <a href="/chores">Back</a>
        """
    cur.execute("UPDATE chores SET chore_name=%s, frequency=%s WHERE chore_id=%s",
                (request.form["chore_name"], request.form["frequency"], id))
    db.commit(); db.close()
    return "<h3>Chore updated</h3><a href='/chores'>Back</a>"

@app.route("/chores/delete/<int:id>", methods=["POST"])
@token_required
def delete_chore(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM chores WHERE chore_id=%s", (id,))
    db.commit(); db.close()
    return "<h3>Chore deleted</h3><a href='/chores'>Back</a>"

# ==================================================
# ASSIGNMENTS CRUD + SEARCH
# ==================================================
@app.route("/assignments")
@token_required
def assignments_page():
    keyword = request.args.get("search", "")
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    
    sql = """
        SELECT a.assignment_id, m.name as member_name, c.chore_name, c.frequency, a.assigned_date, a.is_completed
        FROM chore_assignments a
        JOIN members m ON a.member_id = m.member_id
        JOIN chores c ON a.chore_id = c.chore_id
    """
    if keyword:
        sql += " WHERE m.name LIKE %s OR c.chore_name LIKE %s"
        cur.execute(sql, (f"%{keyword}%", f"%{keyword}%"))
    else:
        cur.execute(sql)
    
    assignments = cur.fetchall(); db.close()
    
    return render_template_string("""
<h1>Chore Assignments</h1>
<form method="GET">
    <input name="search" placeholder="Search assignments" value="{{ request.args.get('search', '') }}">
    <button>Search</button>
    <a href="/assignments">Reset</a>
</form>
<a href="/assignments/add">➕ Add Assignment</a> | <a href="/members">Members</a> | <a href="/chores">Chores</a>
<hr>
{% for a in assignments %}
<p>
<b>{{ a.member_name }}</b> ➡ <b>{{ a.chore_name }}</b> ({{ a.frequency }}) on {{ a.assigned_date }} 
[{{ '✅' if a.is_completed else '❌' }}]
<a href="/assignments/edit/{{ a.assignment_id }}">✏ Edit</a>
<form method="POST" action="/assignments/delete/{{ a.assignment_id }}" style="display:inline;">
<button onclick="return confirm('Delete assignment?')">🗑 Delete</button>
</form>
</p>
{% endfor %}
""", assignments=assignments)

@app.route("/assignments/add", methods=["GET", "POST"])
@token_required
def add_assignment():
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    if request.method == "GET":
        cur.execute("SELECT * FROM members"); members = cur.fetchall()
        cur.execute("SELECT * FROM chores"); chores = cur.fetchall()
        db.close()
        options_members = "".join([f"<option value='{m['member_id']}'>{m['name']}</option>" for m in members])
        options_chores = "".join([f"<option value='{c['chore_id']}'>{c['chore_name']}</option>" for c in chores])
        return f"""
        <h2>Add Assignment</h2>
        <form method="POST">
            Member: <select name="member_id">{options_members}</select><br><br>
            Chore: <select name="chore_id">{options_chores}</select><br><br>
            Date: <input type="date" name="assigned_date" required><br><br>
            Completed: <input type="checkbox" name="is_completed"><br><br>
            <button>Add</button>
        </form>
        <a href="/assignments">Back</a>
        """
    is_completed = 1 if request.form.get("is_completed") == "on" else 0
    cur.execute("INSERT INTO chore_assignments (member_id, chore_id, assigned_date, is_completed) VALUES (%s,%s,%s,%s)",
                (request.form["member_id"], request.form["chore_id"], request.form["assigned_date"], is_completed))
    db.commit(); db.close()
    return "<h3>Assignment added</h3><a href='/assignments'>Back</a>"

@app.route("/assignments/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit_assignment(id):
    db = get_db(); cur = db.cursor(MySQLdb.cursors.DictCursor)
    if request.method == "GET":
        cur.execute("SELECT * FROM chore_assignments WHERE assignment_id=%s", (id,))
        assignment = cur.fetchone()
        cur.execute("SELECT * FROM members"); members = cur.fetchall()
        cur.execute("SELECT * FROM chores"); chores = cur.fetchall()
        db.close()
        options_members = "".join([f"<option value='{m['member_id']}' {'selected' if m['member_id']==assignment['member_id'] else ''}>{m['name']}</option>" for m in members])
        options_chores = "".join([f"<option value='{c['chore_id']}' {'selected' if c['chore_id']==assignment['chore_id'] else ''}>{c['chore_name']}</option>" for c in chores])
        checked = "checked" if assignment["is_completed"] else ""
        return f"""
        <h2>Edit Assignment</h2>
        <form method="POST">
            Member: <select name="member_id">{options_members}</select><br><br>
            Chore: <select name="chore_id">{options_chores}</select><br><br>
            Date: <input type="date" name="assigned_date" value="{assignment['assigned_date']}" required><br><br>
            Completed: <input type="checkbox" name="is_completed" {checked}><br><br>
            <button>Update</button>
        </form>
        <a href="/assignments">Back</a>
        """
    is_completed = 1 if request.form.get("is_completed") == "on" else 0
    cur.execute("""
        UPDATE chore_assignments 
        SET member_id=%s, chore_id=%s, assigned_date=%s, is_completed=%s 
        WHERE assignment_id=%s
    """, (request.form["member_id"], request.form["chore_id"], request.form["assigned_date"], is_completed, id))
    db.commit(); db.close()
    return "<h3>Assignment updated</h3><a href='/assignments'>Back</a>"

@app.route("/assignments/delete/<int:id>", methods=["POST"])
@token_required
def delete_assignment(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM chore_assignments WHERE assignment_id=%s", (id,))
    db.commit(); db.close()
    return "<h3>Assignment deleted</h3><a href='/assignments'>Back</a>"

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
