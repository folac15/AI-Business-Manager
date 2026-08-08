from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os

app = Flask(__name__)
CORS(app)

# ============================================================
# RENDER ENVIRONMENT VARIABLES
# ============================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

# ============================================================
# SUPABASE
# ============================================================

SUPABASE_PROJECT_URL = "https://xfjroysinifwncfjvrsg.supabase.co"

SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmxlIiwicmVmIjoieGZqcm95c2luaWZ3bmNm"
    "anZyc2ciLCJyb2xlIjoiYW5vbiIsImlhdCI6MTc4NDI1NTc0MCwi"
    "ZXhwIjoyMDk5ODMxNzQwfQ."
    "wxKe_cs9n78YhF5nw63crh3pxNnkQW7VGjcqzv3adPs"
)

CUSTOMERS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/customers"
)

BUSINESS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/businesses"
)

BUSINESS_ACCOUNTS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/business_accounts"
)

# ============================================================
# SUPABASE DATABASE HEADERS
# ============================================================

def database_headers():

    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": "Bearer " + SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


# ============================================================
# AUTHENTICATION
# ============================================================

def get_current_user():

    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:

        return None, (
            jsonify({
                "error": "No login session was provided."
            }),
            401
        )

    if not authorization.startswith("Bearer "):

        return None, (
            jsonify({
                "error": "Invalid authorization format."
            }),
            401
        )

    access_token = authorization.replace(
        "Bearer ",
        "",
        1
    ).strip()

    if not access_token:

        return None, (
            jsonify({
                "error": "Login session is empty."
            }),
            401
        )

    try:

        response = requests.get(

            SUPABASE_PROJECT_URL + "/auth/v1/user",

            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": "Bearer " + access_token
            },

            timeout=20
        )

        print(
            "AUTH CHECK STATUS:",
            response.status_code
        )

        print(
            "AUTH CHECK RESPONSE:",
            response.text
        )

        if response.status_code != 200:

            return None, (
                jsonify({
                    "error":
                        "Invalid or expired login session."
                }),
                401
            )

        user = response.json()

        user_id = user.get("id")

        if not user_id:

            return None, (
                jsonify({
                    "error":
                        "Authenticated user ID was not returned."
                }),
                401
            )

        return user, None

    except Exception as error:

        print(
            "AUTH CONNECTION ERROR:",
            str(error)
        )

        return None, (
            jsonify({
                "error":
                    "Unable to verify login session."
            }),
            500
        )


# ============================================================
# WEBSITE
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.route("/index.html")
def index_page():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.route("/<path:filename>")
def serve_files(filename):

    if (
        filename.endswith(".html")
        or filename.endswith(".css")
        or filename.endswith(".js")
    ):

        return send_from_directory(
            ".",
            filename
        )

    return "File not found", 404


@app.route("/style.css")
def style():

    return send_from_directory(
        ".",
        "style.css"
    )


@app.route("/script.js")
def script():

    return send_from_directory(
        ".",
        "script.js"
    )


# ============================================================
# STATUS
# ============================================================

@app.route("/api/status")
def status():

    return jsonify({
        "status": "online",
        "message":
            "AI Business Manager API is working"
    })


# ============================================================
# AI ASSISTANT
# ============================================================

@app.route("/api/ai", methods=["POST"])
def ai_reply():

    data = request.get_json() or {}

    question = data.get(
        "question",
        ""
    ).strip()

    if question == "":

        return jsonify({
            "answer":
                "Please enter your question."
        })

    if not OPENROUTER_API_KEY:

        return jsonify({
            "answer":
                "OpenRouter API key is not configured."
        }), 500

    try:

        response = requests.post(

            "https://openrouter.ai/api/v1/chat/completions",

            headers={
                "Authorization":
                    "Bearer " + OPENROUTER_API_KEY,

                "Content-Type":
                    "application/json"
            },

            json={
                "model":
                    "openai/gpt-oss-20b:free",

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

        print(
            "OPENROUTER STATUS:",
            response.status_code
        )

        if "choices" in result:

            answer = (
                result["choices"][0]
                ["message"]
                ["content"]
            )

        elif "error" in result:

            answer = (
                "OpenRouter error: "
                + str(result["error"])
            )

        else:

            answer = str(result)

    except Exception as error:

        print(
            "OPENROUTER ERROR:",
            str(error)
        )

        answer = (
            "AI service error: "
            + str(error)
        )

    return jsonify({
        "answer": answer
    })


# ============================================================
# ADD CUSTOMER
# ============================================================

@app.route(
    "/api/customers",
    methods=["POST"]
)
def add_customer():

    user, error = get_current_user()

    if error:

        return error

    user_id = user["id"]

    data = request.get_json() or {}

    name = data.get(
        "name",
        ""
    ).strip()

    phone = data.get(
        "phone",
        ""
    ).strip()

    location = data.get(
        "location",
        ""
    ).strip()

    message = data.get(
        "message",
        ""
    ).strip()

    if name == "" or message == "":

        return jsonify({
            "error":
                "Customer name and message are required."
        }), 400

    text = message.lower()

    if "delivery" in text:

        ai_reply = (
            "Yes, we provide delivery services. "
            "Please send us your location."
        )

    elif (
        "price" in text
        or "prices" in text
        or "cost" in text
    ):

        ai_reply = (
            "Thank you for your interest. "
            "Please contact us for our current "
            "prices and offers."
        )

    elif (
        "hello" in text
        or "hi" in text
    ):

        ai_reply = (
            "Hello! Welcome to our business. "
            "How can we help you today?"
        )

    elif "thank" in text:

        ai_reply = (
            "You're welcome. "
            "We are always happy to help."
        )

    else:

        ai_reply = (
            "Thank you for your message. "
            "We will assist you shortly."
        )

    customer = {

        "user_id": user_id,

        "name": name,

        "phone": phone,

        "location": location,

        "message": message,

        "ai_reply": ai_reply,

        "created_at":
            datetime.utcnow().isoformat()
    }

    try:

        response = requests.post(

            CUSTOMERS_URL,

            headers=database_headers(),

            json=customer,

            timeout=20
        )

        if response.status_code not in [
            200,
            201
        ]:

            print(
                "CUSTOMER SAVE ERROR:",
                response.text
            )

            return jsonify({
                "status":
                    response.status_code,

                "error":
                    response.text
            }), response.status_code

        return jsonify({

            "message":
                "Customer saved successfully.",

            "ai_reply":
                ai_reply,

            "user_id":
                user_id
        })

    except Exception as error:

        print(
            "CUSTOMER SAVE CONNECTION ERROR:",
            str(error)
        )

        return jsonify({
            "error":
                "Unable to connect to Supabase."
        }), 500


# ============================================================
# GET CUSTOMERS
# ============================================================

@app.route(
    "/api/customers",
    methods=["GET"]
)
def get_customers():

    user, error = get_current_user()

    if error:

        return error

    user_id = user["id"]

    try:

        response = requests.get(

            CUSTOMERS_URL,

            headers=database_headers(),

            params={

                "select":
                    "id,user_id,name,phone,location,message,ai_reply,created_at",

                "user_id":
                    "eq." + user_id,

                "order":
                    "created_at.desc"
            },

            timeout=20
        )

        if response.status_code != 200:

            print(
                "CUSTOMER LOAD ERROR:",
                response.text
            )

            return jsonify({

                "status":
                    response.status_code,

                "error":
                    response.text

            }), response.status_code

        return jsonify(
            response.json()
        )

    except Exception as error:

        print(
            "CUSTOMER LOAD CONNECTION ERROR:",
            str(error)
        )

        return jsonify({
            "error":
                "Unable to load customers."
        }), 500


# ============================================================
# BUSINESS PROFILE - GET
# ============================================================

@app.route(
    "/api/business",
    methods=["GET"]
)
def get_business():

    try:

        response = requests.get(

            BUSINESS_URL,

            headers=database_headers(),

            params={
                "select": "*",
                "order": "id.desc",
                "limit": 1
            },

            timeout=20
        )

        if response.status_code != 200:

            return jsonify({

                "status":
                    response.status_code,

                "error":
                    response.text

            }), response.status_code

        return jsonify(
            response.json()
        )

    except Exception as error:

        return jsonify({
            "error":
                str(error)
        }), 500


# ============================================================
# BUSINESS PROFILE - SAVE
# ============================================================

@app.route(
    "/api/business",
    methods=["POST"]
)
def save_business():

    data = request.get_json() or {}

    business = {

        "business_name":
            data.get(
                "business_name",
                ""
            ),

        "phone":
            data.get(
                "phone",
                ""
            ),

        "email":
            data.get(
                "email",
                ""
            ),

        "address":
            data.get(
                "address",
                ""
            ),

        "description":
            data.get(
                "description",
                ""
            ),

        "logo":
            data.get(
                "logo",
                ""
            )
    }

    try:

        response = requests.post(

            BUSINESS_URL,

            headers=database_headers(),

            json=business,

            timeout=20
        )

        if response.status_code not in [
            200,
            201
        ]:

            return jsonify({

                "status":
                    response.status_code,

                "error":
                    response.text

            }), response.status_code

        return jsonify({

            "message":
                "Business profile saved successfully."
        })

    except Exception as error:

        return jsonify({
            "error":
                str(error)
        }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
)
