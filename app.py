from flask import Flask, jsonify, request
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
customers = []
@app.route("/")
def home():
    return "AI Business Manager Backend is running!"


@app.route("/api/status")
def status():
    return jsonify({
        "message": "AI Business Manager API is working",
        "status": "online"
    })

@app.route("/api/customers", methods=["POST"])
def add_customer():

    data = request.json

    customer = {
        "name": data.get("name"),
        "message": data.get("message"),
        "date": str(datetime.now())
    }

    customers.append(customer)

    return jsonify({
        "status": "saved",
        "customer": customer
    })


@app.route("/api/customers", methods=["GET"])
def get_customers():

    return jsonify(customers)
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


if __name__ == "__main__":
   app.run(host="0.0.0.0", port=5000, debug=True)
