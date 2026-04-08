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

# ---------------- Data (in-memory) ----------------
tasks = []

# ---------------- HTML Template ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Todo List</title>
    <style>
        body { font-family: Arial; background:#2c3e50; color:white; text-align:center; }
        input, button { padding:10px; margin:5px; }
        table { margin:auto; border-collapse: collapse; width:80%; }
        th, td { border:1px solid #555; padding:10px; }
        th { background:#1a252f; }
        tr.done { background:#2ecc71; }
    </style>
</head>
<body>
    <h1>Todo List</h1>

    <form method="POST" action="/add">
        <input type="text" name="task" placeholder="Ny syssla" required>
        <select name="category">
            <option value="Gemensam">Gemensam</option>
            <option value="Klara">Klara</option>
            <option value="Kristian">Kristian</option>
        </select>
        <button type="submit">Lägg till</button>
    </form>

    <br>

    <table>
        <tr>
            <th>Syssla</th>
            <th>Kategori</th>
            <th>Status</th>
            <th>Namn</th>
            <th>Datum</th>
            <th>Action</th>
        </tr>
        {% for t in tasks %}
        <tr class="{{ 'done' if t.done else '' }}">
            <td>{{ t.task }}</td>
            <td>{{ t.category }}</td>
            <td>{{ '✔️' if t.done else '❌' }}</td>
            <td>{{ t.name }}</td>
            <td>{{ t.date }}</td>
            <td>
                {% if not t.done %}
                <form method="POST" action="/done" style="display:inline;">
                    <input type="hidden" name="id" value="{{ loop.index0 }}">
                    <input type="text" name="name" placeholder="Ditt namn" required>
                    <input type="date" name="date" required>
                    <button type="submit">✔ Klar</button>
                </form>
                {% endif %}
                <form method="POST" action="/delete" style="display:inline;">
                    <input type="hidden" name="id" value="{{ loop.index0 }}">
                    <button type="submit">Ta bort</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
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

    # Create Google Calendar event
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
