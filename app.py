from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests


app = Flask(__name__)
CORS(app)


# ============================================================
# SUPABASE CONFIGURATION
# ============================================================

SUPABASE_PROJECT_URL = "https://xfjroysinifwncfjvrsg.supabase.co"

SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhmanJveXNpbmlmd25jZmp2cnNnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNTU3NDAsImV4cCI6MjA5OTgzMTc0MH0."
    "wxKe_cs9n78YhF5nw63crh3pxNnkQW7VGjcqzv3adPs"
)

SUPABASE_SECRET_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhmanJveXNpbmlmd25jZmp2cnNnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDI1NTc0MCwiZXhwIjoyMDk5ODMxNzQwfQ."
    "cCtu8CzNvV_WpdlzHJtCFh4G8Em3vu7DaxyNrkY-mrk"
)


CUSTOMERS_URL = (
    SUPABASE_PROJECT_URL +
    "/rest/v1/customers"
)

BUSINESS_URL = (
    SUPABASE_PROJECT_URL +
    "/rest/v1/businesses"
)

BUSINESS_ACCOUNTS_URL = (
    SUPABASE_PROJECT_URL +
    "/rest/v1/business_accounts"
)


# ============================================================
# SERVER-SIDE SUPABASE HEADERS
# ============================================================

HEADERS = {
    "apikey": SUPABASE_SECRET_KEY,
    "Authorization": "Bearer " + SUPABASE_SECRET_KEY,
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


# ============================================================
# WEBSITE PAGES
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
# STATUS API
# ============================================================

@app.route("/api/status")
def status():

    return jsonify({
        "status": "online",
        "message": "AI Business Manager API is working"
    })


# ============================================================
# AUTHENTICATED USER
# ============================================================

def get_authenticated_user():

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if not authorization.startswith("Bearer "):

        return (
            None,
            jsonify({
                "error": "Authentication required."
            }),
            401
        )

    access_token = authorization.split(
        " ",
        1
    )[1]

    try:

        response = requests.get(

            SUPABASE_PROJECT_URL +
            "/auth/v1/user",

            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": "Bearer " + access_token
            },

            timeout=15

        )

        if response.status_code != 200:

            return (
                None,
                jsonify({
                    "error":
                    "Invalid or expired login session."
                }),
                401
            )

        user = response.json()

        if not user.get("id"):

            return (
                None,
                jsonify({
                    "error":
                    "User ID could not be determined."
                }),
                401
            )

        return user, None, None

    except Exception as error:

        print(
            "AUTH ERROR:",
            str(error)
        )

        return (
            None,
            jsonify({
                "error":
                "Authentication service error."
            }),
            500
        )


# ============================================================
# AI ASSISTANT API
# ============================================================

@app.route(
    "/api/ai",
    methods=["POST"]
)
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

    try:

        response = requests.post(

            "https://openrouter.ai/api/v1/chat/completions",

            headers={
                "Authorization":
                "Bearer " +
                OPENROUTER_API_KEY,
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

        if "choices" in result:

            answer = (
                result["choices"][0]
                ["message"]
                ["content"]
            )

        else:

            answer = str(result)

    except Exception as error:

        answer = (
            "AI service error: " +
            str(error)
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

    user, error_response, error_status = (
        get_authenticated_user()
    )

    if error_response:

        return (
            error_response,
            error_status
        )

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
            "status": 400,
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

    response = requests.post(

        CUSTOMERS_URL,

        headers=HEADERS,

        json=customer,

        timeout=20

    )

    if response.status_code not in [
        200,
        201
    ]:

        print(
            "SUPABASE CUSTOMER ERROR:",
            response.text
        )

        return jsonify({
            "status":
            response.status_code,

            "error":
            response.text
        }), response.status_code

    return jsonify({

        "status":
        response.status_code,

        "message":
        "Customer saved successfully.",

        "ai_reply":
        ai_reply

    })


# ============================================================
# GET CUSTOMERS
# ============================================================

@app.route(
    "/api/customers",
    methods=["GET"]
)
def get_customers():

    user, error_response, error_status = (
        get_authenticated_user()
    )

    if error_response:

        return (
            error_response,
            error_status
        )

    user_id = user["id"]

    response = requests.get(

        CUSTOMERS_URL,

        headers=HEADERS,

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
            "SUPABASE GET CUSTOMER ERROR:",
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


# ============================================================
# BUSINESS PROFILE API
# ============================================================

@app.route(
    "/api/business",
    methods=["GET"]
)
def get_business():

    response = requests.get(

        BUSINESS_URL,

        headers=HEADERS,

        params={

            "select": "*",

            "order":
            "id.desc",

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

    response = requests.post(

        BUSINESS_URL,

        headers=HEADERS,

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


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
)
