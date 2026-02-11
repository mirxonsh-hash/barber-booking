from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/tg-auth", methods=["POST"])
def tg_auth():
    data = request.json.get("user")

    if not data:
        return jsonify({"error": "No Telegram user data"}), 400

    tg_id = data.get("id")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    username = data.get("username")
    photo_url = data.get("photo_url")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM clients WHERE telegram_id=%s", (tg_id,))
    user = cur.fetchone()

    if not user:
        cur.execute("""
            INSERT INTO clients (telegram_id, first_name, last_name, username, photo_url)
            VALUES (%s,%s,%s,%s,%s)
        """, (tg_id, first_name, last_name, username, photo_url))
        conn.commit()

    cur.close()
    conn.close()

    return jsonify({"success": True})


@app.route("/client-profile")
def client_profile():
    return render_template("client-profile.html")


if __name__ == "__main__":
    app.run(debug=True)
