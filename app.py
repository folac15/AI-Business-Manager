from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os



app = Flask(__name__)
CORS(app)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ===============================
# SUPABASE CONFIGURATION
# ===============================

SUPABASE_URL = "https://xfjroysinifwncfjvrsg.supabase.co/rest/v1/customers"

SUPABASE_STORAGE_URL = "https://xfjroysinifwncfjvrsg.supabase.co/storage/v1/object/business-logos"

BUSINESS_URL = "https://xfjroysinifwncfjvrsg.supabase.co/rest/v1/businesses"

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

@app.route("/<path:filename>")
def serve_files(filename):

    if filename.endswith(".html") or filename.endswith(".css") or filename.endswith(".js"):
        return send_from_directory(".", filename)

    return "File not found", 404

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
    question = data.get("question", "").strip()

    if question == "":
        return jsonify({
            "answer": "Please enter your question."
        })

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-20b:free",
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            },
            timeout=30
        )

        result = response.json()

        if "choices" in result:
            answer = result["choices"][0]["message"]["content"]
        else:
            answer = str(result)

    except Exception as e:
        answer = "AI service error: " + str(e)

    return jsonify({
        "answer": answer
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
    "phone": data.get("phone", "").strip(),
    "location": data.get("location", "").strip(),
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
    "select": "name,phone,location,message,ai_reply,created_at",
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
# BUSINESS PROFILE API
# ===============================

@app.route("/api/business", methods=["GET"])
def get_business():

    response = requests.get(
        BUSINESS_URL,
        headers=HEADERS,
        params={
    "select": "*",
    "order": "id.desc",
    "limit": 1
        }
    )

    if response.status_code != 200:
        return jsonify({
            "status": response.status_code,
            "error": response.text
        }), response.status_code

    return jsonify(response.json())


@app.route("/api/business", methods=["POST"])
def save_business():

    data = request.get_json() or {}

    business = {
    "business_name": data.get("business_name", ""),
    "phone": data.get("phone", ""),
    "email": data.get("email", ""),
    "address": data.get("address", ""),
    "description": data.get("description", ""),
    "logo": data.get("logo", "")
        }
    response = requests.post(
        BUSINESS_URL,
        headers=HEADERS,
        json=business
    )

    if response.status_code not in [200, 201]:
        return jsonify({
            "status": response.status_code,
            "error": response.text
        }), response.status_code

    return jsonify({
        "message": "Business profile saved successfully."
    })
# ===============================
# LOGO UPLOAD API
# ===============================

@app.route("/api/upload-logo", methods=["POST"])
def upload_logo():

    app.logger.info(f"FILES RECEIVED: {request.files}")

    if "logo" not in request.files:
        app.logger.info(f"REQUEST FILE KEYS: {list(request.files.keys())}")

        return jsonify({
            "error": "No logo file provided",
            "received": list(request.files.keys())
        }), 400

    file = request.files["logo"]

    if file.filename == "":
        return jsonify({
            "error": "No selected file"
        }), 400

    filename = file.filename

    storage_url = f"{SUPABASE_STORAGE_URL}/{filename}"

    upload_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": file.content_type
    }

    response = requests.post(
        storage_url,
        headers=upload_headers,
        data=file.read()
    )

    if response.status_code not in [200, 201]:
        return jsonify({
            "error": response.text
        }), response.status_code

    public_url = (
        "https://xfjroysinifwncfjvrsg.supabase.co/storage/v1/object/public/business-logos/"
        + filename
    )

    return jsonify({
        "message": "Logo uploaded successfully",
        "logo_url": public_url
    })
# ===============================
# START SERVER
# ===============================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
)
