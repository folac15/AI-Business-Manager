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

SUPABASE_PROJECT_URL = (
    "https://xfjroysinifwncfjvrsg.supabase.co"
)

# =========================================================
# SUPABASE TABLE URLS
# =========================================================

CUSTOMERS_URL = (
    SUPABASE_PROJECT_URL
    + "/rest/v1/customers"
)

BUSINESS_ACCOUNTS_URL = (
    SUPABASE_PROJECT_URL
    + "/rest/v1/business_accounts"
)

AUTOMATION_SETTINGS_URL = (
    SUPABASE_PROJECT_URL
    + "/rest/v1/automation_settings"
)

# =========================================================
# SUPABASE HEADERS
# =========================================================

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SECRET_KEY,
    "Authorization":
        "Bearer " + str(SUPABASE_SECRET_KEY),
    "Content-Type":
        "application/json"
}


# =========================================================
# WEBSITE
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

    if filename.endswith(
        (".html", ".css", ".js")
    ):

        return send_from_directory(
            ".",
            filename
        )

    return "File not found", 404


# =========================================================
# STATUS
# =========================================================

@app.route("/api/status")
def status():

    return jsonify({
        "status": "online",
        "message":
            "NexaFlow AI API is working"
    })


# =========================================================
# AUTHENTICATED SUPABASE USER
# =========================================================

def get_authenticated_user():

    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:

        return None

    if not authorization.startswith(
        "Bearer "
    ):

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

            SUPABASE_PROJECT_URL
            + "/auth/v1/user",

            headers={

                "apikey":
                    SUPABASE_SECRET_KEY,

                "Authorization":
                    "Bearer " + access_token

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

@app.route(
    "/api/ai",
    methods=["POST"]
)
def ai_reply():

    data = request.get_json(
        silent=True
    ) or {}

    question = str(
        data.get(
            "question",
            ""
        )
    ).strip()

    conversation = data.get(
        "conversation",
        []
    )

    if not question:

        return jsonify({
            "answer":
                "Please enter your question."
        }), 400

    if not OPENROUTER_API_KEY:

        return jsonify({
            "answer":
                "OpenRouter API key is not configured."
        }), 500

    messages = [

        {
            "role":
                "system",

            "content":
                NEXAFLOW_SYSTEM_PROMPT
        }

    ]

    if isinstance(
        conversation,
        list
    ):

        for item in conversation:

            if not isinstance(
                item,
                dict
            ):

                continue

            role = item.get(
                "role"
            )

            content = item.get(
                "content"
            )

            if role not in (
                "user",
                "assistant"
            ):

                continue

            if content is None:

                continue

            content = str(
                content
            ).strip()

            if not content:

                continue

            messages.append({

                "role":
                    role,

                "content":
                    content

            })

    messages.append({

        "role":
            "user",

        "content":
            question

    })

    # Keep the system prompt plus
    # the latest 20 conversation messages.
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
                    "Bearer "
                    + OPENROUTER_API_KEY,

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
                    + str(error_info)

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

            "answer":
                answer

        })

    except Exception as error:

        print(
            "AI service exception:",
            error
        )

        return jsonify({

            "answer":
                "AI service connection error: "
                + str(error)

        }), 500
        # =========================================================
# AUTOMATION SETTINGS
# =========================================================

@app.route(
    "/api/automation",
    methods=["GET"]
)
def get_automation_settings():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
            "Invalid or expired login session."
        }), 401

    try:

        response = requests.get(

            AUTOMATION_SETTINGS_URL,

            headers=SUPABASE_HEADERS,

            params={
                "select": "*",
                "user_id":
                "eq." + user["id"],
                "limit": "1"
            },

            timeout=15
        )

        print(
            "Automation settings GET status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "Automation GET error:",
                response.text
            )

            return jsonify({
                "error":
                response.text
            }), response.status_code

        settings = response.json()

        if settings:

            return jsonify({
                "automation":
                settings[0]
            })

        # No row yet: return default settings
        return jsonify({
            "automation": {
                "user_id": user["id"],
                "ai_replies": True,
                "message_automation": True,
                "task_automation": True
            }
        })

    except Exception as error:

        print(
            "Automation GET exception:",
            error
        )

        return jsonify({
            "error":
            str(error)
        }), 500


# =========================================================
# SAVE AUTOMATION SETTINGS
# =========================================================

@app.route(
    "/api/automation",
    methods=["POST"]
)
def save_automation_settings():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
            "Invalid or expired login session."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    ai_replies = bool(
        data.get(
            "ai_replies",
            True
        )
    )

    message_automation = bool(
        data.get(
            "message_automation",
            True
        )
    )

    task_automation = bool(
        data.get(
            "task_automation",
            True
        )
    )

    automation = {

        "user_id":
        user["id"],

        "ai_replies":
        ai_replies,

        "message_automation":
        message_automation,

        "task_automation":
        task_automation,

        "updated_at":
        datetime.utcnow().isoformat()
    }

    try:

        response = requests.post(

            AUTOMATION_SETTINGS_URL,

            headers={
                **SUPABASE_HEADERS,

                "Prefer":
                "resolution=merge-duplicates,return=representation"
            },

            json=automation,

            timeout=15
        )

        print(
            "Automation SAVE status:",
            response.status_code
        )

        if response.status_code not in (
            200,
            201
        ):

            print(
                "Automation SAVE error:",
                response.text
            )

            return jsonify({
                "error":
                response.text
            }), response.status_code

        try:

            result = response.json()

        except ValueError:

            result = []

        saved = (

            result[0]

            if isinstance(result, list)
            and result

            else automation
        )

        return jsonify({

            "message":
            "Automation settings saved successfully.",

            "automation":
            saved

        })

    except Exception as error:

        print(
            "Automation SAVE exception:",
            error
        )

        return jsonify({
            "error":
            str(error)
        }), 500


# =========================================================
# UPDATE ONE AUTOMATION SETTING
# =========================================================

@app.route(
    "/api/automation/toggle",
    methods=["POST"]
)
def toggle_automation():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
            "Invalid or expired login session."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    setting = str(
        data.get(
            "setting",
            ""
        )
    ).strip()

    value = data.get(
        "value"
    )

    allowed_settings = {

        "ai_replies",

        "message_automation",

        "task_automation"

    }

    if setting not in allowed_settings:

        return jsonify({
            "error":
            "Invalid automation setting."
        }), 400

    if not isinstance(
        value,
        bool
    ):

        return jsonify({
            "error":
            "Automation value must be true or false."
        }), 400

    update_data = {

        setting:
        value,

        "updated_at":
        datetime.utcnow().isoformat()

    }

    try:

        # First check whether the user's
        # automation row already exists.

        check = requests.get(

            AUTOMATION_SETTINGS_URL,

            headers=SUPABASE_HEADERS,

            params={

                "select": "id",

                "user_id":
                "eq." + user["id"],

                "limit": "1"

            },

            timeout=15
        )

        if check.status_code != 200:

            return jsonify({

                "error":
                check.text

            }), check.status_code

        existing = check.json()

        # =================================================
        # ROW EXISTS -> UPDATE
        # =================================================

        if existing:

            response = requests.patch(

                AUTOMATION_SETTINGS_URL,

                headers={
                    **SUPABASE_HEADERS,
                    "Prefer":
                    "return=representation"
                },

                params={

                    "user_id":
                    "eq." + user["id"]

                },

                json=update_data,

                timeout=15
            )

        # =================================================
        # ROW DOES NOT EXIST -> CREATE
        # =================================================

        else:

            new_settings = {

                "user_id":
                user["id"],

                "ai_replies":
                True,

                "message_automation":
                True,

                "task_automation":
                True

            }

            new_settings[
                setting
            ] = value

            new_settings[
                "updated_at"
            ] = datetime.utcnow().isoformat()

            response = requests.post(

                AUTOMATION_SETTINGS_URL,

                headers={
                    **SUPABASE_HEADERS,
                    "Prefer":
                    "return=representation"
                },

                json=new_settings,

                timeout=15
            )

        print(
            "Automation TOGGLE status:",
            response.status_code
        )

        if response.status_code not in (
            200,
            201,
            204
        ):

            print(
                "Automation TOGGLE error:",
                response.text
            )

            return jsonify({

                "error":
                response.text

            }), response.status_code

        try:

            result = response.json()

        except ValueError:

            result = []

        return jsonify({

            "message":
            "Automation setting updated successfully.",

            "setting":
            setting,

            "value":
            value,

            "automation":
            result[0]
            if isinstance(result, list)
            and result
            else None

        })

    except Exception as error:

        print(
            "Automation TOGGLE exception:",
            error
        )

        return jsonify({

            "error":
            str(error)

        }), 500
        # =========================================================
# BUSINESS ACCOUNT
# =========================================================

@app.route("/api/business", methods=["GET", "POST"])
def business_account():

    user = get_authenticated_user()

    if not user:
        return jsonify({
            "error": "Invalid or expired login session."
        }), 401

    user_id = user["id"]

    # GET BUSINESS
    if request.method == "GET":

        try:
            response = requests.get(
                BUSINESS_ACCOUNTS_URL,
                headers=SUPABASE_HEADERS,
                params={
                    "select": "*",
                    "user_id": "eq." + user_id,
                    "limit": "1"
                },
                timeout=15
            )

            if response.status_code != 200:
                return jsonify({
                    "error": response.text
                }), response.status_code

            businesses = response.json()

            if businesses:
                return jsonify({
                    "business": businesses[0]
                })

            return jsonify({
                "business": None
            })

        except Exception as error:
            return jsonify({
                "error": str(error)
            }), 500


    # SAVE BUSINESS
    data = request.get_json(silent=True) or {}

    business_data = {
        "user_id": user_id,
        "business_name": str(data.get("business_name", "")).strip(),
        "owner_name": str(data.get("owner_name", "")).strip(),
        "phone": str(data.get("phone", "")).strip(),
        "email": str(data.get("email", "")).strip(),
        "address": str(data.get("address", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "logo": str(data.get("logo", "")).strip(),
        "updated_at": datetime.utcnow().isoformat()
    }

    try:

        check = requests.get(
            BUSINESS_ACCOUNTS_URL,
            headers=SUPABASE_HEADERS,
            params={
                "select": "id",
                "user_id": "eq." + user_id,
                "limit": "1"
            },
            timeout=15
        )

        if check.status_code != 200:
            return jsonify({
                "error": check.text
            }), check.status_code

        existing = check.json()

        # UPDATE EXISTING BUSINESS
        if existing:

            business_id = existing[0]["id"]

            response = requests.patch(
                BUSINESS_ACCOUNTS_URL,
                headers={
                    **SUPABASE_HEADERS,
                    "Prefer": "return=representation"
                },
                params={
                    "id": "eq." + str(business_id),
                    "user_id": "eq." + user_id
                },
                json=business_data,
                timeout=15
            )

        # CREATE NEW BUSINESS
        else:

            response = requests.post(
                BUSINESS_ACCOUNTS_URL,
                headers={
                    **SUPABASE_HEADERS,
                    "Prefer": "return=representation"
                },
                json=business_data,
                timeout=15
            )

        if response.status_code not in (200, 201):
            return jsonify({
                "error": response.text
            }), response.status_code

        try:
            saved = response.json()
        except ValueError:
            saved = []

        if isinstance(saved, list) and saved:
            saved_business = saved[0]
        else:
            saved_business = business_data

        return jsonify({
            "success": True,
            "business": saved_business,
            "message": "Business settings saved successfully."
        })

    except Exception as error:

        return jsonify({
            "error": str(error)
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
