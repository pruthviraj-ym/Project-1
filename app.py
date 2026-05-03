from flask import Flask, render_template, request, redirect, session
import sqlite3, pickle, pandas as pd, os

# 🔥 FIXED PATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = "secret123"

# Load ML model
model = pickle.load(open("studentperformance/model.pkl", "rb"))
scaler = pickle.load(open("studentperformance/scaler.pkl", "rb"))

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("studentperformance/students.db")
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT DEFAULT 'user')''')

    cur.execute('''CREATE TABLE IF NOT EXISTS results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        result TEXT,
        score REAL)''')

    cur.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not cur.fetchone():
        cur.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                    ("admin","admin123","admin"))

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["username"]
        p=request.form["password"]

        conn=sqlite3.connect("studentperformance/students.db")
        cur=conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user=cur.fetchone()
        conn.close()

        if user:
            session["user"]=u
            session["role"]=user[3]

            if user[3]=="admin":
                return redirect("/admin")
            return redirect("/dashboard")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        conn=sqlite3.connect("studentperformance/students.db")
        conn.execute("INSERT INTO users(username,password) VALUES(?,?)",
                     (request.form["username"], request.form["password"]))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("register.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn=sqlite3.connect("studentperformance/students.db")
    cur=conn.cursor()

    cur.execute("SELECT COUNT(*) FROM results")
    total=cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM results WHERE result='Good Performance'")
    good=cur.fetchone()[0]

    bad=total-good
    conn.close()

    return render_template("dashboard.html", total=total, good=good, bad=bad)

# ---------------- PREDICT ----------------
@app.route("/predict", methods=["GET","POST"])
def predict():
    if "user" not in session:
        return redirect("/")

    if request.method=="POST":
        data = [
            float(request.form["hours"]),
            float(request.form["attendance"]),
            float(request.form["previous"]),
            float(request.form["assignments"]),
            float(request.form["extra"]),
            float(request.form["sleep"])
        ]

        scaled=scaler.transform([data])
        res=model.predict(scaled)[0]

        result="Good Performance" if res==1 else "Needs Improvement"

        conn=sqlite3.connect("studentperformance/students.db")
        conn.execute("INSERT INTO results(username,result,score) VALUES(?,?,?)",
                     (session["user"], result, sum(data)))
        conn.commit()
        conn.close()

        return render_template("predict.html", result=result)

    return render_template("predict.html")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if session.get("role")!="admin":
        return redirect("/")

    conn=sqlite3.connect("studentperformance/students.db")
    users=conn.execute("SELECT * FROM users").fetchall()
    results=conn.execute("SELECT * FROM results").fetchall()
    conn.close()

    return render_template("admin.html", users=users, results=results)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
