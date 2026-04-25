from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import re
import os
from openai import OpenAI

app = Flask(__name__)
app.secret_key = "azachat_secret"

# 🔑 ВСТАВЬ СВОЙ API KEY СЮДА
client = OpenAI(api_key="ТВОЙ_API_КЛЮЧ")

DB_NAME = "azachat.db"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room TEXT,
        user TEXT,
        message TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


def save_message(room, user, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (room, user, message) VALUES (?, ?, ?)",
        (room, user, message)
    )
    conn.commit()
    conn.close()


def load_messages(room):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user, message FROM messages WHERE room=? ORDER BY id ASC",
        (room,)
    )
    data = c.fetchall()
    conn.close()
    return data


# ---------------- AI HYBRID ----------------
def get_bot_reply(text, user, history):
    text_lower = text.lower().strip()

    # 🤖 1. ПЫТАЕМСЯ OPENAI (как ChatGPT)
    try:
        messages = [
            {
                "role": "system",
                "content": "Ты AzaBot — умный, дружелюбный AI ассистент. Отвечай коротко и понятно."
            }
        ]

        # 📚 добавляем память диалога
        for u, m in history[-10:]:
            role = "assistant" if u == "AzaBot 🤖" else "user"
            messages.append({"role": role, "content": m})

        messages.append({"role": "user", "content": text})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        return response.choices[0].message.content

    except Exception:
        # ⚠️ FALLBACK (если нет квоты или API сломался)

        # 💬 приветствия
        if "привет" in text_lower:
            return f"Привет {user} 👋"

        if "как дела" in text_lower:
            return "Я работаю в офлайн режиме 🤖"

        if "кто ты" in text_lower:
            return "Я AzaBot PRO — гибрид AI ассистент 🧠"

        if "что ты умеешь" in text_lower:
            return (
                "Я умею:\n"
                "🤖 Отвечать на вопросы\n"
                "🧮 Считать примеры\n"
                "💬 Работать без интернета API\n"
                "🧠 Переключаться в AI режим\n"
                "🌐 Искать ответы (в будущем)"
            )

        # 🧮 калькулятор
        try:
            expr = re.sub(r'[^0-9+\-*/().]', '', text)
            if expr and any(char.isdigit() for char in expr):
                return f"🧮 Ответ: {eval(expr)}"
        except:
            pass

        return "Я пока не знаю ответ 🤖 но учусь..."


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    room = "general"
    messages = load_messages(room)

    return render_template(
        "index.html",
        messages=messages,
        user=session["user"]
    )


@app.route("/send", methods=["POST"])
def send():
    if "user" not in session:
        return redirect(url_for("login"))

    msg = request.form["message"]
    user = session["user"]
    room = "general"

    save_message(room, user, msg)

    history = load_messages(room)
    bot = get_bot_reply(msg, user, history)

    save_message(room, "AzaBot 🤖", bot)

    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["user"] = request.form["username"]
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        session["user"] = request.form["username"]
        return redirect(url_for("home"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
