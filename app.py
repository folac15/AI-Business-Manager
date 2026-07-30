from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os

app = Flask(__name__)
CORS(app)

# ===============================
# SUPABASE CONFIGURATION
# ===============================

SUPABASE_URL = "https://xfjroysinifwncfjvrsg.supabase.co/rest/v1/customers"

SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ===============================
# WEBSITE PAGES
# ===============================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/index.html")
def index_page():
    return send_from_directory(".", "index.html")

@app.route("/dashboard.html")
def dashboard():
    return send_from_directory(".", "dashboard.html")

@app.route("/customers.html")
def customers():
    return send_from_directory(".", "customers.html")

@app.route("/posts.html")
def posts():
    return send_from_directory(".", "posts.html")

@app.route("/post_history.html")
def post_history():
    return send_from_directory(".", "post_history.html")

@app.route("/videos.html")
def videos():
    return send_from_directory(".", "videos.html")

@app.route("/settings.html")
def settings():
    return send_from_directory(".", "settings.html")

@app.route("/ai_assistant.html")
def ai_assistant():
    return send_from_directory(".", "ai_assistant.html")

@app.route("/style.css")
def style():
    return send_from_directory(".", "style.css")

@app.route("/script.js")
def script():
    return send_from_directory(".", "script.js")

# ===============================
# STATUS API
# ===============================

@app.route("/api/status")
def status():

    return jsonify({
        "status": "online",
        "message": "AI Business Manager API is working"
    })
    # ===============================
# AI ASSISTANT API
# ===============================

@app.route("/api/ai", methods=["POST"])
def ai_reply():

    data = request.get_json() or {}

    question = data.get("question", "").strip().lower()

    if question == "":
        answer = "Please enter your question."

    elif "delivery" in question:
        answer = "Yes, we provide delivery services. Please send us your location."

    elif "price" in question or "prices" in question or "cost" in question:
        answer = "Thank you for your interest. Please contact us for our current prices and offers."

    elif "hello" in question or "hi" in question:
        answer = "Hello! Welcome to our business. How can we help you today?"

    elif "thank" in question:
        answer = "You're welcome. We are always happy to help."

    else:
        answer = "Thank you for your message. We will assist you shortly."

    return jsonify({
        "response": answer
    })


# ===============================
# ADD CUSTOMER
# ===============================

@app.route("/api/customers", methods=["POST"])
def add_customer():

    data = request.get_json() or {}

    name = data.get("name", "").strip()

    message = data.get("message", "").strip()

    if name == "" or message == "":
        return jsonify({
            "status": 400,
            "error": "Customer name and message are required."
        }), 400

    text = message.lower()

    if "delivery" in text:
        ai_reply = "Yes, we provide delivery services. Please send us your location."

    elif "price" in text or "prices" in text or "cost" in text:
        ai_reply = "Thank you for your interest. Please contact us for our current prices and offers."

    elif "hello" in text or "hi" in text:
        ai_reply = "Hello! Welcome to our business. How can we help you today?"

    elif "thank" in text:
        ai_reply = "You're welcome. We are always happy to help."

    else:
        ai_reply = "Thank you for your message. We will assist you shortly."

    customer = {
        "name": name,
        "message": message,
        "ai_reply": ai_reply,
        "created_at": datetime.utcnow().isoformat()
    }

    response = requests.post(
        SUPABASE_URL,
        headers=HEADERS,
        json=customer
    )

    if response.status_code not in [200, 201]:
        return jsonify({
            "status": response.status_code,
            "error": response.text
        }), response.status_code

    return jsonify({
        "status": response.status_code,
        "message": "Customer saved successfully.",
        "ai_reply": ai_reply
    })


# ===============================
# GET CUSTOMERS
# ===============================

@app.route("/api/customers", methods=["GET"])
def get_customers():

    response = requests.get(
        SUPABASE_URL,
        headers=HEADERS,
        params={
            "select": "name,message,ai_reply,created_at",
            "order": "created_at.desc"
        }
    )

    if response.status_code != 200:
        return jsonify({
            "status": response.status_code,
            "error": response.text
        }), response.status_code

    return jsonify(response.json())
# ===============================
# START SERVER
# ===============================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
)
