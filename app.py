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

# ---------------- HTML ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Todo List</title>

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, Arial;
            background: #121212;
            color: #f1f1f1;
            margin: 0;
            padding: 15px;
        }

        h1 {
            text-align: center;
            margin-bottom: 20px;
        }

        .container {
            max-width: 900px;
            margin: auto;
        }

        form {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
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
            background: #4CAF50;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }

        button:hover {
            background: #45a049;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e1e1e;
            border-radius: 10px;
            overflow: hidden;
        }

        th {
            background: #000;
            padding: 12px;
            text-align: left;
        }

        td {
            padding: 10px;
            border-bottom: 1px solid #333;
        }

        tr.done {
            background: #1b5e20;
        }

        .actions form {
            display: inline;
        }

        .delete-btn {
            background: #e74c3c;
        }

        .delete-btn:hover {
            background: #c0392b;
        }

        .done-btn {
            background: #3498db;
        }

        .done-btn:hover {
            background: #2980b9;
        }

        @media (max-width: 600px) {
            form {
                flex-direction: column;
            }

            input, select, button {
                width: 100%;
            }

            table, th, td {
                font-size: 12px;
            }
        }
    </style>
</head>
<body>

<div class="container">
    <h1>📋 Todo List</h1>

    <form method="POST" action="/add">
        <input type="text" name="task" placeholder="Ny syssla" required>

        <select name="category">
            <option value="Gemensam">Gemensam</option>
            <option value="Klara">Klara</option>
            <option value="Kristian">Kristian</option>
        </select>

        <button type="submit">➕ Lägg till</button>
    </form>

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
            <td class="actions">

                {% if not t.done %}
                <form method="POST" action="/done">
                    <input type="hidden" name="id" value="{{ loop.index0 }}">
                    <input type="text" name="name" placeholder="Namn" required>
                    <input type="date" name="date" required>
                    <button class="done-btn" type="submit">✔ Klar</button>
                </form>
                {% endif %}

                <form method="POST" action="/delete">
                    <input type="hidden" name="id" value="{{ loop.index0 }}">
                    <button class="delete-btn" type="submit">Ta bort</button>
                </form>

            </td>
        </tr>
        {% endfor %}
    </table>
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
