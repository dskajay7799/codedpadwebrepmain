# app.py
import os
import string
import random
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 5000))

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)


def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pastes (
            id SERIAL PRIMARY KEY,
            passkey VARCHAR(12) UNIQUE NOT NULL,
            code TEXT NOT NULL,
            language VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("DB ready")
    except Exception as e:
        print("DB ERROR:", e)


init_db()


def generate_passkey(length=6):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def get_expiry(exp):
    now = datetime.utcnow()
    if exp == "1h":
        return now + timedelta(hours=1)
    if exp == "24h":
        return now + timedelta(hours=24)
    if exp == "7d":
        return now + timedelta(days=7)
    return None


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


@app.route("/save", methods=["POST"])
def save():
    try:
        data = request.get_json()
        code = data.get("code", "").strip()
        lang = data.get("language", "plaintext")
        expiry = data.get("expiry", "never")

        if not code:
            return jsonify({"error": "empty"}), 400

        conn = get_db()
        cur = conn.cursor()

        while True:
            key = generate_passkey()
            cur.execute("SELECT 1 FROM pastes WHERE passkey=%s", (key,))
            if not cur.fetchone():
                break

        cur.execute("""
        INSERT INTO pastes (passkey, code, language, expires_at)
        VALUES (%s,%s,%s,%s)
        """, (key, code, lang, get_expiry(expiry)))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"passkey": key})

    except Exception as e:
        print("SAVE ERROR:", e)
        return jsonify({"error": "fail"}), 500


@app.route("/load/<key>")
def load(key):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        SELECT code, language, created_at, expires_at
        FROM pastes WHERE passkey=%s
        """, (key,))

        row = cur.fetchone()

        if not row:
            return jsonify({"error": "not found"}), 404

        code, lang, created, exp = row

        if exp and datetime.utcnow() > exp:
            return jsonify({"error": "expired"}), 410

        return jsonify({
            "code": code,
            "language": lang,
            "saved_at": created.isoformat()
        })

    except Exception as e:
        print("LOAD ERROR:", e)
        return jsonify({"error": "fail"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
