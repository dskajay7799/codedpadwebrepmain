import os
import string
import random
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 5000))

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set!")

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)


# ─────────────────────────────────────────────
# Database Connection (FIXED: SSL added)
# ─────────────────────────────────────────────
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


# ─────────────────────────────────────────────
# Init DB safely
# ─────────────────────────────────────────────
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
        print("✅ DB initialized")

    except Exception as e:
        print("❌ DB INIT ERROR:", e)


init_db()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def generate_passkey(length=6):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def get_expiry(expiry_str):
    now = datetime.utcnow()

    if expiry_str == "1h":
        return now + timedelta(hours=1)
    elif expiry_str == "24h":
        return now + timedelta(hours=24)
    elif expiry_str == "7d":
        return now + timedelta(days=7)
    else:
        return None


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.route("/save", methods=["POST"])
def save_code():
    try:
        data = request.get_json()

        code = data.get("code", "").strip()
        language = data.get("language", "plaintext")
        expiry = data.get("expiry", "never")

        if not code:
            return jsonify({"error": "Code cannot be empty"}), 400

        conn = get_db()
        cur = conn.cursor()

        # unique passkey
        while True:
            passkey = generate_passkey()
            cur.execute("SELECT 1 FROM pastes WHERE passkey=%s", (passkey,))
            if not cur.fetchone():
                break

        expires_at = get_expiry(expiry)

        cur.execute("""
            INSERT INTO pastes (passkey, code, language, expires_at)
            VALUES (%s, %s, %s, %s)
        """, (passkey, code, language, expires_at))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"passkey": passkey})

    except Exception as e:
        print("SAVE ERROR:", e)
        return jsonify({"error": "Failed to save code"}), 500


@app.route("/load/<passkey>", methods=["GET"])
def load_code(passkey):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT code, language, created_at, expires_at
            FROM pastes
            WHERE passkey=%s
        """, (passkey,))

        row = cur.fetchone()

        if not row:
            return jsonify({"error": "Code not found"}), 404

        code, language, created_at, expires_at = row

        if expires_at and datetime.utcnow() > expires_at:
            return jsonify({"error": "Code expired"}), 410

        return jsonify({
            "code": code,
            "language": language,
            "saved_at": created_at.isoformat()
        })

    except Exception as e:
        print("LOAD ERROR:", e)
        return jsonify({"error": "Failed to load code"}), 500


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
    
