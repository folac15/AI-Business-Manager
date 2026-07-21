from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)


SUPABASE_URL = "https://xfjroysinifwncfjvrsg.supabase.co/rest/v1/customers"

import os

SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


@app.route("/")
def home():
    return "AI Business Manager Backend is running!"


@app.route("/api/status")
def status():
    return jsonify({
        "message": "AI Business Manager API is working",
        "status": "online"
    })


@app.route("/api/ai", methods=["POST"])
def ai_reply():

    data = request.json
    question = data.get("question", "").lower()

    if "price" in question:
        answer = "Thank you for your interest. Please contact us for our current prices and offers."

    elif "hello" in question or "hi" in question:
        answer = "Hello! Welcome to our business. How can we help you today?"

    elif "delivery" in question:
        answer = "We provide delivery services. Please send your location."

    else:
        answer = "Thank you for your message. We will assist you shortly."

    return jsonify({
        "response": answer
    })


@app.route("/api/customers", methods=["POST"])
def add_customer():

    data = request.json
    message = data.get("message", "")

    if "price" in message.lower():
        ai_reply = "Thank you for your interest. Please contact us for our current prices and offers."
    elif "hello" in message.lower() or "hi" in message.lower():
        ai_reply = "Hello! Welcome to our business. How can we help you today?"
    elif "delivery" in message.lower():
        ai_reply = "We provide delivery services. Please send your location."
    else:
        ai_reply = "Thank you for your message. We will assist you shortly."

    customer = {
        "name": data.get("name"),
        "message": message,
        "ai_reply": ai_reply,
        "created_at": datetime.utcnow().isoformat()
    }

    response = requests.post(
        SUPABASE_URL,
        headers=HEADERS,
        json=customer
    )

    return jsonify({
        "status": response.status_code,
        "result": response.text,
        "ai_reply": ai_reply
    })


@app.route("/api/customers", methods=["GET"])
def get_customers():

    response = requests.get(
        SUPABASE_URL,
        headers=HEADERS
    )

    return jsonify(response.json())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
