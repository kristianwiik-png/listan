from flask import Flask, render_template_string, request, redirect, session
import sqlite3
import os

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

SCOPES = ['https://www.googleapis.com/auth/calendar']

# ---------------- USERS ----------------
USERS = {
    "kristian": "LÄGG_IN_LÖSENORD",
    "person2": "LÄGG_IN_LÖSENORD"
}

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        category TEXT,
        done INTEGER,
        name TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

def get_tasks():
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()
    c.execute("SELECT * FROM tasks")
    rows = c.fetchall()
    conn.close()

    tasks = []
    for r in rows:
        tasks.append({
            "id": r[0],
            "task": r[1],
            "category": r[2],
            "done": bool(r[3]),
            "name": r[4],
            "date": r[5]
        })

    return tasks

# ---------------- GOOGLE ----------------
def get_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS and USERS[username] == password:
            session["user"] = username
            return redirect("/")
        return "Fel login"

    return """
    <div style="text-align:center; margin-top:100px;">
        <h2>Login</h2>
        <form method="POST">
            <input name="username" placeholder="Användarnamn"><br><br>
            <input type="password" name="password" placeholder="Lösenord"><br><br>
            <button type="submit">Logga in</button>
        </form>
    </div>
    """

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ---------------- HTML ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Todo</title>

<style>
body { font-family: Arial; background:#0f172a; color:white; margin:0; }
.container { max-width:900px; margin:auto; padding:15px; }
.card { background:#1e293b; padding:15px; margin:10px 0; border-radius:10px; }
.done { background:#14532d; }
input, select { padding:8px; margin:5px; }
button { padding:8px; margin:5px; cursor:pointer; }
</style>

</head>
<body>

<div class="container">

<h3>Inloggad som {{ user }}</h3>
<a href="/logout">Logga ut</a>

<h1>Todo</h1>

<form method="POST" action="/add">
    <input name="task" placeholder="Task" required>
    <select name="category">
        <option>Gemensam</option>
        <option>Klara</option>
        <option>Kristian</option>
    </select>
    <button>Lägg till</button>
</form>

{% for t in tasks %}
<div class="card {{ 'done' if t.done else '' }}">
    <b>{{ t.task }}</b><br>
    {{ t.category }}<br>
    Status: {{ 'Klar' if t.done else 'Ej klar' }}

    {% if not t.done %}
    <form method="POST" action="/done">
        <input type="hidden" name="id" value="{{ t.id }}">
        <input name="name" placeholder="Namn" required>
        <input type="date" name="date" required>
        <button>Klar</button>
    </form>
    {% endif %}

    <form method="POST" action="/delete">
        <input type="hidden" name="id" value="{{ t.id }}">
        <button>Ta bort</button>
    </form>
</div>
{% endfor %}

</div>

</body>
</html>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")

    return render_template_string(HTML, tasks=get_tasks(), user=session["user"])

@app.route("/add", methods=["POST"])
def add():
    if "user" not in session:
        return redirect("/login")

    task = request.form.get("task")
    category = request.form.get("category")

    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    c.execute("INSERT INTO tasks (task, category, done, name, date) VALUES (?, ?, 0, '', '')",
              (task, category))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/done", methods=["POST"])
def done():
    if "user" not in session:
        return redirect("/login")

    task_id = request.form.get("id")
    name = request.form.get("name")
    date_str = request.form.get("date")

    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    c.execute("UPDATE tasks SET done=1, name=?, date=? WHERE id=?",
              (name, date_str, task_id))

    conn.commit()
    conn.close()

    try:
        service = get_service()

        event = {
            'summary': f"{name} klarade en uppgift",
            'start': {'dateTime': date_str + "T10:00:00", 'timeZone': 'Europe/Stockholm'},
            'end': {'dateTime': date_str + "T11:00:00", 'timeZone': 'Europe/Stockholm'},
        }

        service.events().insert(calendarId='primary', body=event).execute()

    except Exception as e:
        print("Calendar error:", e)

    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete():
    if "user" not in session:
        return redirect("/login")

    task_id = request.form.get("id")

    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))

    conn.commit()
    conn.close()

    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
