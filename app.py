from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import sqlite3, io, qrcode, random, string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_FILE = "event_system.db"

# ---------------- Database ----------------
def init_db():
    if not os.path.exists(DB_FILE):
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            sponsors TEXT,
            total_passes INTEGER,
            qr_width REAL,
            qr_height REAL,
            max_uses INTEGER
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pass (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            code TEXT UNIQUE,
            used_count INTEGER DEFAULT 0
        )""")
        con.commit()
        con.close()

def get_db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con

def query_db(query, args=(), one=False):
    con = get_db()
    cur = con.execute(query, args)
    rv = cur.fetchall()
    con.commit()
    con.close()
    return (rv[0] if rv else None) if one else rv

init_db()
# --------- Auto create default admin user ---------
try:
    existing_admin = query_db("SELECT * FROM user WHERE username=?", ["admin"], one=True)
    if not existing_admin:
        query_db(
            "INSERT INTO user (username,password_hash,role) VALUES (?,?,?)",
            ["admin", generate_password_hash("admin123"), "admin"]
        )
except Exception as e:
    print("Admin creation error:", e)


# ---------------- Utilities ----------------
def generate_pass_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

# ---------------- Login ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        user = query_db("SELECT * FROM user WHERE username=?", [username], one=True)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            if user["role"]=="admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"]=="worker":
                return redirect(url_for("worker_dashboard"))
            elif user["role"]=="client":
                return redirect(url_for("client_dashboard"))
        flash("Invalid credentials","danger")
        return render_template("login.html", username=username)
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- Admin ----------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    events = query_db("SELECT * FROM event")
    users = query_db("SELECT * FROM user")
    return render_template("admin_dashboard.html", events=events, users=users)

@app.route("/admin/create_event", methods=["POST"])
def create_event():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    name = request.form["name"]
    date = request.form["date"]
    sponsors = request.form.get("sponsors","")
    total_passes = int(request.form["total_passes"])
    max_uses = int(request.form["max_uses"])
    qr_width = float(request.form.get("qr_width",3))  # in cm
    qr_height = float(request.form.get("qr_height",3))  # in cm
    query_db("INSERT INTO event (name,date,sponsors,total_passes,max_uses,qr_width,qr_height) VALUES (?,?,?,?,?,?,?)",
             [name,date,sponsors,total_passes,max_uses,qr_width,qr_height])
    flash("Event created successfully","success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/create_user", methods=["POST"])
def create_user():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]
    try:
        query_db("INSERT INTO user (username,password_hash,role) VALUES (?,?,?)",
                 [username, generate_password_hash(password), role])
        flash(f"{role} created successfully","success")
    except:
        flash("Username already exists","danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_event/<int:event_id>")
def delete_event(event_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    query_db("DELETE FROM event WHERE id=?", [event_id])
    query_db("DELETE FROM pass WHERE event_id=?", [event_id])
    flash("Event deleted","success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    query_db("DELETE FROM user WHERE id=?", [user_id])
    flash("User deleted","success")
    return redirect(url_for("admin_dashboard"))

# ---------------- Worker ----------------
@app.route("/worker")
def worker_dashboard():
    if session.get("role") != "worker":
        return redirect(url_for("login"))
    events = query_db("SELECT * FROM event")
    return render_template("worker_dashboard.html", events=events)

@app.route("/worker/manual_entry", methods=["POST"])
def manual_entry():
    data = request.get_json()
    code = data.get("pass_code")
    pass_row = query_db("SELECT * FROM pass WHERE code=?", [code], one=True)
    if not pass_row:
        return jsonify({"status":"error","message":"Invalid Pass"})
    event = query_db("SELECT * FROM event WHERE id=?",[pass_row["event_id"]], one=True)
    if pass_row["used_count"] < event["max_uses"]:
        query_db("UPDATE pass SET used_count=used_count+1 WHERE id=?", [pass_row["id"]])
        remaining = max(0, event["max_uses"] - (pass_row["used_count"]+1))
        return jsonify({"status":"success","message":f"✅ Entry Allowed. Remaining uses: {remaining}"})
    return jsonify({"status":"error","message":"⚠ Pass fully used"})

@app.route("/worker/report")
def worker_report():
    if session.get("role") != "worker":
        return redirect(url_for("login"))
    events = query_db("SELECT * FROM event")
    report=[]
    for e in events:
        used = query_db("SELECT SUM(used_count) as used FROM pass WHERE event_id=?", [e["id"]], one=True)["used"] or 0
        remaining = e["total_passes"] * e["max_uses"] - used
        report.append({"event":e["name"], "used":used, "remaining":remaining})
    return jsonify(report)

# ---------------- Client ----------------
@app.route("/client")
def client_dashboard():
    if session.get("role") != "client":
        return redirect(url_for("login"))
    events = query_db("SELECT * FROM event")
    report=[]
    for e in events:
        used = query_db("SELECT SUM(used_count) as used FROM pass WHERE event_id=?", [e["id"]], one=True)["used"] or 0
        remaining = e["total_passes"] * e["max_uses"] - used
        report.append({"event":e["name"], "used":used, "remaining":remaining})
    return render_template("client_dashboard.html", report=report)

# ---------------- PDF Passes ----------------
@app.route("/event/<int:event_id>/generate_passes")
def generate_passes(event_id):
    event = query_db("SELECT * FROM event WHERE id=?", [event_id], one=True)
    if not event:
        return "Event not found", 404

    total_passes = event["total_passes"]
    qr_width = event["qr_width"] * cm
    qr_height = event["qr_height"] * cm
    qr_margin = 10  # points

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x_margin=10
    y_margin=10
    x=x_margin
    y=height-y_margin-qr_height
    passes_per_row = int((width - 2*x_margin)//(qr_width+qr_margin))
    row_count=0

    for _ in range(total_passes):
        pass_code = generate_pass_id()
        qr_img = qrcode.make(pass_code).convert("RGB")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        c.drawInlineImage(Image.open(qr_buffer), x, y, width=qr_width, height=qr_height)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x+qr_width/2, y-10, pass_code)

        x += qr_width+qr_margin
        row_count+=1
        if row_count>=passes_per_row:
            row_count=0
            x=x_margin
            y-=qr_height+20
            if y<y_margin+qr_height:
                c.showPage()
                y=height-y_margin-qr_height

        query_db("INSERT OR IGNORE INTO pass (event_id, code, used_count) VALUES (?,?,?)",
                 [event_id, pass_code,0])

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"{event['name'].replace(' ','_')}_passes.pdf",
                     mimetype="application/pdf")

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run()

