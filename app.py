from flask import Flask, render_template_string, request, redirect
from datetime import datetime, timedelta
import os

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

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

# ---------------- HTML (Card-based UI) ----------------
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
            margin-bottom: 20px;
        }

        form.add-form {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }

        input, select, button {
            padding: 10px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
        }

        input, select {
            flex: 1;
            min-width: 120px;
        }

        button {
            background: #22c55e;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }

        button:hover {
            background: #16a34a;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 12px;
        }

        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }

        .card.done {
            background: #14532d;
        }

        .title {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 8px;
        }

        .meta {
            font-size: 13px;
            opacity: 0.8;
            margin-bottom: 10px;
        }

        .status {
            font-size: 14px;
            margin-bottom: 10px;
        }

        .actions {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .actions form {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .actions input {
            flex: 1;
        }

        .btn-done {
            background: #3b82f6;
        }

        .btn-delete {
            background: #ef4444;
        }

        .btn-delete:hover {
            background: #dc2626;
        }

        @media (max-width: 600px) {
            form.add-form {
                flex-direction: column;
            }

            input, select, button {
                width: 100%;
            }
        }
    </style>
</head>
<body>

<div class="container">
    <h1>📋 Todo App</h1>

    <form class="add-form" method="POST" action="/add">
        <input type="text" name="task" placeholder="Ny syssla" required>

        <select name="category">
            <option value="Gemensam">Gemensam</option>
            <option value="Klara">Klara</option>
            <option value="Kristian">Kristian</option>
        </select>

        <button type="submit">➕ Lägg till</button>
    </form>

    <div class="grid">
        {% for t in tasks %}
        <div class="card {{ 'done' if t.done else '' }}">

            <div class="title">{{ t.task }}</div>
            <div class="meta">Kategori: {{ t.category }}</div>

            <div class="status">
                Status: {{ '✔ Klar' if t.done else '❌ Ej klar' }}
            </div>

            <div class="meta">
                Namn: {{ t.name if t.name else '-' }}<br>
                Datum: {{ t.date if t.date else '-' }}
            </div>

            <div class="actions">

                {% if not t.done %}
                <form method="POST" action="/done">
                    <input type="hidden" name="id" value="{{ loop.index0 }}">
                    <input type="text" name="name" placeholder="Namn" required>
                    <input type="date" name="date" required>
                    <button class="btn-done" type="submit">✔ Klar</button>
                </form>
                {% endif %}

                <form method="POST" action="/delete">
                    <input type="hidden" name="id" value="{{ loop.index0 }}">
                    <button class="btn-delete" type="submit">Ta bort</button>
                </form>

            </div>
        </div>
        {% endfor %}
    </div>

</div>

</body>
</html>
"""

# ---------------- Routes ----------------
@app.route("/")
def index():
    return render_template_string(HTML, tasks=tasks)

@app.route("/add", methods=["POST"])
def add():
    task = request.form.get("task")
    category = request.form.get("category")

    tasks.append({
        "task": task,
        "category": category,
        "done": False,
        "name": "",
        "date": ""
    })

    return redirect("/")

@app.route("/done", methods=["POST"])
def done():
    task_id = int(request.form.get("id"))
    name = request.form.get("name")
    date_str = request.form.get("date")

    tasks[task_id]["done"] = True
    tasks[task_id]["name"] = name
    tasks[task_id]["date"] = date_str

    # Google Calendar
    try:
        service = get_service()

        start = datetime.strptime(date_str, "%Y-%m-%d")
        end = start + timedelta(hours=1)

        event = {
            'summary': f"{tasks[task_id]['task']} - Klar av {name}",
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': 'Europe/Stockholm',
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': 'Europe/Stockholm',
            },
        }

        service.events().insert(calendarId='primary', body=event).execute()

    except Exception as e:
        print("Calendar error:", e)

    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete():
    task_id = int(request.form.get("id"))
    tasks.pop(task_id)
    return redirect("/")

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
