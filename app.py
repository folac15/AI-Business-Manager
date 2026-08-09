from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os


app = Flask(__name__)
CORS(app)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")


# =========================================================
# SUPABASE CONFIGURATION
# =========================================================

SUPABASE_PROJECT_URL = (
    "https://xfjroysinifwncfjvrsg.supabase.co"
)


CUSTOMERS_URL = (
    SUPABASE_PROJECT_URL +
    "/rest/v1/customers"
)


BUSINESS_ACCOUNTS_URL = (
    SUPABASE_PROJECT_URL +
    "/rest/v1/business_accounts"
)


# =========================================================
# SUPABASE SERVER HEADERS
# =========================================================

SUPABASE_HEADERS = {

    "apikey":
    SUPABASE_SECRET_KEY,

    "Authorization":
    "Bearer " + str(SUPABASE_SECRET_KEY),

    "Content-Type":
    "application/json"

}


# =========================================================
# WEBSITE PAGES
# =========================================================

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
        or
        filename.endswith(".css")
        or
        filename.endswith(".js")
    ):

        return send_from_directory(
            ".",
            filename
        )

    return "File not found", 404


# =========================================================
# STATUS API
# =========================================================

@app.route("/api/status")
def status():

    return jsonify({

        "status":
        "online",

        "message":
        "NexaFlow AI API is working"

    })


# =========================================================
# HELPER — GET LOGGED-IN USER
# =========================================================

def get_authenticated_user():

    authorization =
    request.headers.get("Authorization")


    if not authorization:

        return None


    if not authorization.startswith(
        "Bearer "
    ):

        return None


    access_token =
    authorization.replace(
        "Bearer ",
        "",
        1
    ).strip()


    if not access_token:

        return None


    try:

        response = requests.get(

            SUPABASE_PROJECT_URL +
            "/auth/v1/user",

            headers={

                "apikey":
                SUPABASE_SECRET_KEY,

                "Authorization":
                "Bearer " +
                access_token

            },

            timeout=15

        )


        if response.status_code != 200:

            print(
                "Supabase user verification failed:",
                response.text
            )

            return None


        user =
        response.json()


        if not user.get("id"):

            return None


        return user


    except Exception as error:

        print(
            "User authentication error:",
            error
        )

        return None


# =========================================================
# AI ASSISTANT API
# =========================================================

@app.route(
    "/api/ai",
    methods=["POST"]
)
def ai_reply():

    data =
    request.get_json() or {}


    question =
    data.get(
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

                        "role":
                        "user",

                        "content":
                        question

                    }

                ]

            },

            timeout=30

        )


        result =
        response.json()


        if "choices" in result:

            answer =
            result["choices"][0]["message"]["content"]

        else:

            answer =
            str(result)


    except Exception as error:

        answer =
        "AI service error: " + str(error)


    return jsonify({

        "answer":
        answer

    })


# =========================================================
# GET BUSINESS ACCOUNT
# =========================================================

@app.route(
    "/api/business",
    methods=["GET"]
)
def get_business():

    user =
    get_authenticated_user()


    if not user:

        return jsonify({

            "error":
            "Invalid or expired login session."

        }), 401


    user_id =
    user["id"]


    try:

        response = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=SUPABASE_HEADERS,

            params={

                "select":
                "*",

                "user_id":
                "eq." + user_id,

                "limit":
                "1"

            },

            timeout=15

        )


        if response.status_code != 200:

            print(
                "Business account error:",
                response.text
            )

            return jsonify({

                "error":
                response.text

            }), response.status_code


        businesses =
        response.json()


        if not businesses:

            return jsonify({

                "business":
                None

            })


        return jsonify({

            "business":
            businesses[0]

        })


    except Exception as error:

        print(
            "Business API error:",
            error
        )

        return jsonify({

            "error":
            str(error)

        }), 500


# =========================================================
# SAVE BUSINESS ACCOUNT
# =========================================================

@app.route(
    "/api/business",
    methods=["POST"]
)
def save_business():

    user =
    get_authenticated_user()


    if not user:

        return jsonify({

            "error":
            "Invalid or expired login session."

        }), 401


    data =
    request.get_json() or {}


    business = {

        "user_id":
        user["id"],

        "business_name":
        data.get(
            "business_name",
            ""
        ),

        "owner_name":
        data.get(
            "owner_name",
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

            BUSINESS_ACCOUNTS_URL,

            headers={
                **SUPABASE_HEADERS,
                "Prefer":
                "return=representation"
            },

            json=business,

            timeout=15

        )


        if response.status_code not in [
            200,
            201
        ]:

            return jsonify({

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


# =========================================================
# ADD CUSTOMER
# =========================================================

@app.route(
    "/api/customers",
    methods=["POST"]
)
def add_customer():

    user =
    get_authenticated_user()


    if not user:

        return jsonify({

            "error":
            "Invalid or expired login session."

        }), 401


    data =
    request.get_json() or {}


    name =
    data.get(
        "name",
        ""
    ).strip()


    phone =
    data.get(
        "phone",
        ""
    ).strip()


    location =
    data.get(
        "location",
        ""
    ).strip()


    message =
    data.get(
        "message",
        ""
    ).strip()


    if name == "" or message == "":

        return jsonify({

            "error":
            "Customer name and message are required."

        }), 400


    # =====================================================
    # SIMPLE AI REPLY
    # =====================================================

    text =
    message.lower()


    if "delivery" in text:

        ai_reply = (
            "Yes, we provide delivery services. "
            "Please send us your location."
        )


    elif (
        "price" in text
        or
        "prices" in text
        or
        "cost" in text
    ):

        ai_reply = (
            "Thank you for your interest. "
            "Please contact us for our current "
            "prices and offers."
        )


    elif (
        "hello" in text
        or
        "hi" in text
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

        "name":
        name,

        "phone":
        phone,

        "location":
        location,

        "message":
        message,

        "ai_reply":
        ai_reply,

        "created_at":
        datetime.utcnow().isoformat()

    }


    try:

        response = requests.post(

            CUSTOMERS_URL,

            headers={
                **SUPABASE_HEADERS,
                "Prefer":
                "return=representation"
            },

            json=customer,

            timeout=15

        )


        if response.status_code not in [
            200,
            201
        ]:

            print(
                "Customer save error:",
                response.text
            )

            return jsonify({

                "error":
                response.text

            }), response.status_code


        return jsonify({

            "message":
            "Customer saved successfully.",

            "ai_reply":
            ai_reply

        })


    except Exception as error:

        print(
            "Customer save exception:",
            error
        )

        return jsonify({

            "error":
            str(error)

        }), 500


# =========================================================
# GET CUSTOMERS
# =========================================================

@app.route(
    "/api/customers",
    methods=["GET"]
)
def get_customers():

    user =
    get_authenticated_user()


    if not user:

        return jsonify({

            "error":
            "Invalid or expired login session."

        }), 401


    try:

        response = requests.get(

            CUSTOMERS_URL,

            headers=SUPABASE_HEADERS,

            params={

                "select":
                "id,name,phone,location,message,ai_reply,created_at",

                "order":
                "created_at.desc"

            },

            timeout=15

        )


        print(
            "Supabase customers status:",
            response.status_code
        )


        if response.status_code != 200:

            print(
                "Supabase customers error:",
                response.text
            )

            return jsonify({

                "error":
                response.text

            }), response.status_code


        return jsonify(
            response.json()
        )


    except Exception as error:

        print(
            "Get customers exception:",
            error
        )

        return jsonify({

            "error":
            str(error)

        }), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )

)
