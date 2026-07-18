from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

SUPABASE_URL = "https://xfjroysinifwncfjvrsg.supabase.co/rest/v1/customers"

SUPABASE_KEY = "sb_publishable_ITqFQ7q90A6lkl8bzDQQEA_eiOuX9VR"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
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

    customer = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "message": data.get("message"),
        "created_at": datetime.now().isoformat()
    }

    response = requests.post(
        SUPABASE_URL,
        headers=HEADERS,
        json=customer
    )

    return jsonify({
        "message": "Customer saved successfully",
        "data": response.json()
    })


@app.route("/api/customers", methods=["GET"])
def get_customers():

    response = requests.get(
        SUPABASE_URL,
        headers=HEADERS
    )

    return jsonify(response.json())


@app.route("/api/customers/<id>", methods=["DELETE"])
def delete_customer(id):

    response = requests.delete(
        f"{SUPABASE_URL}?id=eq.{id}",
        headers=HEADERS
    )

    return jsonify({
        "message": "Customer deleted"
    })


if __name__ == "__main__":
    app.run(debug=True)
