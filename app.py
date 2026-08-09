from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

SUPABASE_PROJECT_URL = "https://xfjroysinifwncfjvrsg.supabase.co"

CUSTOMERS_URL = SUPABASE_PROJECT_URL + "/rest/v1/customers"

BUSINESS_ACCOUNTS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/business_accounts"
)

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SECRET_KEY,
    "Authorization": "Bearer " + str(SUPABASE_SECRET_KEY),
    "Content-Type": "application/json",
}


# =========================================================
# WEBSITE
# =========================================================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/index.html")
def index_page():
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def serve_files(filename):
    if filename.endswith((".html", ".css", ".js")):
        return send_from_directory(".", filename)

    return "File not found", 404


# =========================================================
# STATUS
# =========================================================

@app.route("/api/status")
def status():
    return jsonify({
        "status": "online",
        "message": "NexaFlow AI API is working"
    })


# =========================================================
# AUTHENTICATED SUPABASE USER
# =========================================================

def get_authenticated_user():

    authorization = request.headers.get("Authorization")

    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    access_token = authorization.replace(
        "Bearer ",
        "",
        1
    ).strip()

    if not access_token:
        return None

    try:

        response = requests.get(
            SUPABASE_PROJECT_URL + "/auth/v1/user",

            headers={
                "apikey": SUPABASE_SECRET_KEY,
                "Authorization": "Bearer " + access_token
            },

            timeout=15
        )

        if response.status_code != 200:

            print(
                "Supabase user verification failed:",
                response.text
            )

            return None

        user = response.json()

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
# NEXAFLOW AI SYSTEM PROMPT
# =========================================================

NEXAFLOW_SYSTEM_PROMPT = """
You are NexaFlow AI, the intelligent conversational assistant
inside the NexaFlow Business Management Platform.

Help with:

- Business management
- Customer service
- Marketing
- Sales
- Business ideas
- Business planning
- Mathematics
- Physics
- Engineering
- Education
- General knowledge
- Writing
- Communication
- Problem solving

CONVERSATION:

Always use the conversation history supplied by the application.

Understand short follow-up messages from context.

If the user says "give me an example", give an example of the
current topic.

If the user says "another one" or "give me another example",
give a different example of the current topic.

If the user says "solve it", identify the most recent relevant
exercise or problem and solve it.

If the user says "why", explain the previous statement or result.

If the user says "make it easier", explain the previous answer
using simpler English.

If the user says "continue" or "go on", continue the current topic.

MATHEMATICS AND PHYSICS:

- Explain concepts clearly.
- Give formulas when useful.
- Define variables when useful.
- Show reasoning.
- Give examples when requested.
- Create exercises when requested.
- Solve exercises step by step when requested.
- Make another example different from the previous one.
- Use simple English unless advanced detail is requested.
- Use practical Cameroon-related contexts when appropriate.

EDUCATION:

- Explain before giving an example when appropriate.
- Do not give an exercise's answer unless the student asks.
- Correct mistakes politely.

BUSINESS:

- Give practical recommendations.
- Consider small and medium businesses.
- Consider African and Cameroonian realities when relevant.
- Do not invent prices, statistics, regulations or market data.

Do not ask unnecessary clarification questions.

When a reasonable interpretation is available, answer directly.

Be accurate, natural, helpful and conversational.

Do not fabricate information.

Do not claim to have performed an action that you did not perform.

Do not repeatedly say that you are an AI.
"""


# =========================================================
# AI ASSISTANT
# =========================================================

@app.route("/api/ai", methods=["POST"])
def ai_reply():

    data = request.get_json(silent=True) or {}

    question = str(
        data.get("question", "")
    ).strip()

    conversation = data.get(
        "conversation",
        []
    )

    if not question:

        return jsonify({
            "answer": "Please enter your question."
        }), 400

    if not OPENROUTER_API_KEY:

        return jsonify({
            "answer":
            "OpenRouter API key is not configured."
        }), 500

    messages = [
        {
            "role": "system",
            "content": NEXAFLOW_SYSTEM_PROMPT
        }
    ]

    if isinstance(conversation, list):

        for item in conversation:

            if not isinstance(item, dict):
                continue

            role = item.get("role")

            content = item.get("content")

            if role not in (
                "user",
                "assistant"
            ):
                continue

            if content is None:
                continue

            content = str(content).strip()

            if not content:
                continue

            messages.append({
                "role": role,
                "content": content
            })

    messages.append({
        "role": "user",
        "content": question
    })

    # Keep system prompt + most recent 20 messages.
    if len(messages) > 21:

        messages = (
            [messages[0]]
            +
            messages[-20:]
        )

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

                "messages":
                messages
            },

            timeout=60
        )

        try:

            result = response.json()

        except ValueError:

            result = {}

        print(
            "OpenRouter status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "OpenRouter error:",
                result
            )

            error_info = result.get(
                "error",
                result
            )

            return jsonify({

                "answer":
                "AI service error: "
                +
                str(error_info)

            }), 500

        choices = result.get(
            "choices",
            []
        )

        if choices:

            message = choices[0].get(
                "message",
                {}
            )

            answer = str(
                message.get(
                    "content",
                    ""
                )
            ).strip()

        else:

            answer = ""

        if not answer:

            answer = (
                "The AI did not return an answer."
            )

        return jsonify({
            "answer": answer
        })

    except Exception as error:

        print(
            "AI service exception:",
            error
        )

        return jsonify({

            "answer":
            "AI service connection error: "
            +
            str(error)

        }), 500


# =========================================================
# GET BUSINESS ACCOUNT
# =========================================================

@app.route(
    "/api/business",
    methods=["GET"]
)
def get_business():

    user = get_authenticated_user()

    if not user:

        return jsonify({

            "error":
            "Invalid or expired login session."

        }), 401

    try:

        response = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=SUPABASE_HEADERS,

            params={

                "select": "*",

                "user_id":
                "eq." + user["id"],

                "limit": "1"

            },

            timeout=15
        )

        if response.status_code != 200:

            return jsonify({

                "error":
                response.text

            }), response.status_code

        businesses = response.json()

        return jsonify({

            "business":
            businesses[0]
            if businesses
            else None

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

    user = get_authenticated_user()

    if not user:

        return jsonify({

            "error":
            "Invalid or expired login session."

        }), 401

    data = request.get_json(
        silent=True
    ) or {}

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

        if response.status_code not in (
            200,
            201
        ):

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

    user = get_authenticated_user()

    if not user:

        return jsonify({

            "error":
            "Invalid or expired login session."

        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    location = str(
        data.get(
            "location",
            ""
        )
    ).strip()

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not name or not message:

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

    elif any(
        word in text
        for word in (
            "price",
            "prices",
            "cost"
        )
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

        "user_id":
        user["id"],

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

        if response.status_code not in (
            200,
            201
        ):

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

    user = get_authenticated_user()

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

                "select": (
                    "id,user_id,name,phone,location,"
                    "message,ai_reply,created_at"
                ),

                "user_id":
                "eq." + user["id"],

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

        customers = response.json()

        print(

            "Customers returned for user:",

            user["id"],

            "Count:",

            len(customers)

        )

        return jsonify(customers)

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
# APPLICATION START
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(

        host="0.0.0.0",

        port=port

)
