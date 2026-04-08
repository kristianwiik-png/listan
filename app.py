from flask import Flask, render_template_string, request, redirect, session
from datetime import datetime, timedelta
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
    "kristian": "baffebaffe",
    "klara": "baffebaffe"
}

# ---------------- Google Auth ----------------
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

# ---------------- Data ----------------
tasks = []

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS and USERS[username] == password:
            session["user"] = username
            return redirect("/")
        return "Fel användarnamn eller lösenord"

    return """
    <div style="text-align:center; margin-top:100px; font-family:Arial;">
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
    <title>Todo App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, Arial;
            background: #0f172a;
            color: #e2e8f0;
        }

        .container {
            max-width: 1000px;
            margin: auto;
            padding: 15px;
        }

        h1 {
            text-align: center;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 12px;
        }

        .card {
            background: #1e293b;
            padding: 15px;
            border-radius: 12px;
        }

        .card.done {
            background: #14532d;
        }

        .btn {
            padding: 8px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
        }

        .done-btn { background: #3b82f6; color: white; }
        .delete-btn { background: #ef4444; color: white; }

        input, select {
            padding: 8px;
            border-radius: 6px;
            border: none;
        }

        form.add-form {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }

        @media (max-width: 600px) {
            form.add-form {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>

<div class="container">

    <div class="topbar">
        <div>Inloggad som: {{ user }}</div>
        <a href="/logout" style="color:#fff;">Logga ut</a>
    </div>

    <h1>📋 Todo App</h1>

    <form class="add-form" method="POST" action="/add">
        <input type="text" name="task" placeholder="Ny syssla" required>

        <select name="category">
            <option value="Gemensam">Gemensam</option>
            <option value="Klara">Klara</option>
            <option value="Kristian">Kristian</option>
        </select>

        <button class="btn done-btn" type="submit">➕ Lägg till</button>
    </form>

    <div class="grid">
        {% for t in tasks %}
        <div class="card {{ 'done' if t.done else '' }}">

            <b>{{ t.task }}</b><br><br>
            Kategori: {{ t.category }}<br>
            Status: {{ '✔ Klar' if t.done else '❌ Ej klar' }}<br>
            Namn: {{ t.name or '-' }}<br>
            Datum: {{ t.date or '-' }}<br><br>

            {% if not t.done %}
            <form method="POST" action="/done">
                <input type="hidden" name="id" value="{{ loop.index0 }}">
                <input type="text" name="name" placeholder="Namn" required>
                <input type="date" name="date" required>
                <button class="btn done-btn">✔ Klar</button>
            </form>
            {% endif %}

            <form method="POST" action="/delete">
                <input type="hidden" name="id" value="{{ loop.index0 }}">
                <button class="btn delete-btn">Ta bort</button>
            </form>

        </div>
        {% endfor %}
    </div>

</div>

</body>
</html>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")

    return render_template_string(HTML, tasks=tasks, user=session["user"])

@app.route("/add", methods=["POST"])
def add():
    if "user" not in session:
        return redirect("/login")

    tasks.append({
        "task": request.form.get("task"),
        "category": request.form.get("category"),
        "done": False,
        "name": "",
        "date": ""
    })

    return redirect("/")

@app.route("/done", methods=["POST"])
def done():
    if "user" not in session:
        return redirect("/login")

    task_id = int(request.form.get("id"))
    name = request.form.get("name")
    date_str = request.form.get("date")

    tasks[task_id]["done"] = True
    tasks[task_id]["name"] = name
    tasks[task_id]["date"] = date_str

    try:
        service = get_service()

        start = datetime.strptime(date_str, "%Y-%m-%d")
        end = start + timedelta(hours=1)

        event = {
            'summary': f"{tasks[task_id]['task']} - Klar av {name}",
            'start': {'dateTime': start.isoformat(), 'timeZone': 'Europe/Stockholm'},
            'end': {'dateTime': end.isoformat(), 'timeZone': 'Europe/Stockholm'},
        }

        service.events().insert(calendarId='primary', body=event).execute()

    except Exception as e:
        print("Calendar error:", e)

    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete():
    if "user" not in session:
        return redirect("/login")

    task_id = int(request.form.get("id"))
    tasks.pop(task_id)
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
