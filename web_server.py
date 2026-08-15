from flask import Flask, request, jsonify, render_template_string
import sys
import os
import threading

ROOT_DIR = "/mnt/jarvis"

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.brain import JarvisBrain

app = Flask(__name__)

print("[JARVIS] Loading brain...")
brain = JarvisBrain()
print("[JARVIS] Brain loaded successfully.")

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JARVIS</title>

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    background: #071018;
    color: #dff9ff;
    font-family: Arial, sans-serif;
}

.header {
    padding: 18px;
    background: #0b1822;
    border-bottom: 1px solid #16445a;
    display: flex;
    justify-content: space-between;
}

.title {
    font-size: 24px;
    font-weight: bold;
    color: #67e8ff;
}

.online {
    color: #58f59b;
}

.container {
    max-width: 1100px;
    margin: auto;
    padding: 15px;
}

.card {
    background: #0b1720;
    border: 1px solid #163d4d;
    border-radius: 14px;
    padding: 15px;
    margin-bottom: 15px;
}

.card-title {
    color: #67e8ff;
    margin-bottom: 12px;
    font-weight: bold;
}

.chat {
    min-height: 300px;
    max-height: 55vh;
    overflow-y: auto;
    padding: 10px;
}

.message {
    padding: 12px;
    margin: 8px 0;
    border-radius: 10px;
    white-space: pre-wrap;
}

.user {
    background: #10394a;
}

.jarvis {
    background: #101f29;
    border-right: 3px solid #67e8ff;
}

.activity {
    background: #050b10;
    border-radius: 10px;
    padding: 12px;
    min-height: 120px;
    max-height: 300px;
    overflow-y: auto;
    direction: ltr;
    text-align: left;
    font-family: monospace;
}

.event {
    padding: 7px 0;
    border-bottom: 1px solid #102631;
}

.input-row {
    display: flex;
    gap: 8px;
}

input {
    flex: 1;
    padding: 14px;
    background: #071018;
    border: 1px solid #20556b;
    border-radius: 10px;
    color: white;
    font-size: 16px;
}

button {
    padding: 14px 20px;
    border: 0;
    border-radius: 10px;
    background: #0b718f;
    color: white;
    font-size: 16px;
}

button:disabled {
    opacity: 0.5;
}

.status {
    color: #9bd7e6;
    font-size: 13px;
    margin-top: 8px;
}
</style>
</head>

<body>

<div class="header">
    <div class="title">J A R V I S</div>
    <div class="online">● ONLINE</div>
</div>

<div class="container">

    <div class="card">
        <div class="card-title">المحادثة</div>

        <div id="chat" class="chat">
            <div class="message jarvis">
                JARVIS متصل بالمخ الحقيقي.
            </div>
        </div>

        <div class="input-row">
            <input
                id="message"
                placeholder="اكتب لـ JARVIS..."
                autocomplete="off"
            >

            <button id="send" onclick="sendMessage()">
                إرسال
            </button>
        </div>

        <div id="status" class="status">
            جاهز
        </div>
    </div>

    <div class="card">
        <div class="card-title">LIVE ACTIVITY</div>

        <div id="activity" class="activity">
            <div class="event">
                [SYSTEM] Web interface connected
            </div>
            <div class="event">
                [SYSTEM] JarvisBrain loaded
            </div>
        </div>
    </div>

</div>

<script>

const input = document.getElementById("message");
const sendButton = document.getElementById("send");
const statusBox = document.getElementById("status");

input.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

function addMessage(text, type) {
    const chat = document.getElementById("chat");

    const item = document.createElement("div");
    item.className = "message " + type;
    item.textContent = text;

    chat.appendChild(item);
    chat.scrollTop = chat.scrollHeight;
}

function addActivity(text) {
    const box = document.getElementById("activity");

    const item = document.createElement("div");
    item.className = "event";

    const now = new Date().toLocaleTimeString();

    item.textContent = "[" + now + "] " + text;

    box.appendChild(item);
    box.scrollTop = box.scrollHeight;
}

async function sendMessage() {

    const text = input.value.trim();

    if (!text) {
        return;
    }

    input.value = "";
    sendButton.disabled = true;

    addMessage(text, "user");
    addActivity("USER → " + text);

    statusBox.textContent = "JARVIS يفكر...";

    addActivity("JARVIS → processing request");

    try {

        const response = await fetch("/api/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: text
            })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Unknown server error");
        }

        addMessage(data.answer, "jarvis");

        addActivity("JARVIS → response received");

        statusBox.textContent = "جاهز";

    } catch (error) {

        addMessage(
            "حدث خطأ: " + error.message,
            "jarvis"
        );

        addActivity(
            "ERROR → " + error.message
        );

        statusBox.textContent = "حدث خطأ";

    } finally {

        sendButton.disabled = false;
        input.focus();
    }
}

</script>

</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/ask", methods=["POST"])
def ask():

    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "ok": False,
            "error": "الرسالة فارغة."
        }), 400

    print()
    print("=" * 60)
    print("[WEB USER]")
    print(message)
    print("=" * 60)

    try:

        answer = brain.ask(message)

        print("[JARVIS RESPONSE]")
        print(answer)
        print("=" * 60)

        return jsonify({
            "ok": True,
            "answer": str(answer)
        })

    except Exception as error:

        print("[JARVIS ERROR]")
        print(repr(error))

        return jsonify({
            "ok": False,
            "error": str(error)
        }), 500


if __name__ == "__main__":

    print()
    print("=" * 60)
    print(" JARVIS WEB INTERFACE")
    print("=" * 60)
    print()
    print("Tablet:")
    print("http://192.168.1.9:8000")
    print()
    print("JARVIS Brain: READY")
    print()

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
        threaded=True
    )
