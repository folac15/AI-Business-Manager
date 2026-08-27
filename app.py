from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import requests
import os
import time
import threading
import traceback

app = Flask(__name__)
CORS(app)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

SUPABASE_PROJECT_URL = "https://xfjroysinifwncfjvrsg.supabase.co"

WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get(
    "WHATSAPP_BUSINESS_ACCOUNT_ID"
)


# =========================================================
# OPENROUTER AI MODELS
# =========================================================

OPENROUTER_PRIMARY_MODEL = "openai/gpt-oss-20b:free"

OPENROUTER_FREE_ROUTER_MODEL = "openrouter/free"


# =========================================================
# SUPABASE TABLE URLS
# =========================================================

CUSTOMERS_URL = SUPABASE_PROJECT_URL + "/rest/v1/customers"
BUSINESS_ACCOUNTS_URL = SUPABASE_PROJECT_URL + "/rest/v1/business_accounts"
AUTOMATION_SETTINGS_URL = SUPABASE_PROJECT_URL + "/rest/v1/automation_settings"
AI_CONVERSATIONS_URL = SUPABASE_PROJECT_URL + "/rest/v1/ai_conversations"
INTEGRATIONS_URL = SUPABASE_PROJECT_URL + "/rest/v1/integrations"
MESSAGES_URL = SUPABASE_PROJECT_URL + "/rest/v1/messages"


# =========================================================
# TIME
# =========================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# SUPABASE HEADERS
# =========================================================

def supabase_headers(prefer=None):
    headers = {
        "apikey": str(SUPABASE_SECRET_KEY or ""),
        "Authorization": "Bearer " + str(
            SUPABASE_SECRET_KEY or ""
        ),
        "Content-Type": "application/json"
    }

    if prefer:
        headers["Prefer"] = prefer

    return headers


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
# API STATUS
# =========================================================

@app.route("/api/status")
def status():
    return jsonify({
        "status": "online",
        "message": "NexaFlow AI API is working"
    })


# =========================================================
# AUTHENTICATED USER
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

    if not SUPABASE_SECRET_KEY:
        print("SUPABASE_SECRET_KEY is not configured.")
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

        print(
            "Supabase authentication status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "Supabase authentication error:",
                response.text
            )

            return None

        user = response.json()

        if not user.get("id"):
            return None

        return user

    except Exception as error:

        print(
            "Authentication exception:",
            error
        )

        traceback.print_exc()

        return None


# =========================================================
# SYSTEM PROMPT
# =========================================================

NEXAFLOW_SYSTEM_PROMPT = """
You are NexaFlow AI, the intelligent conversational assistant inside the NexaFlow Business Management Platform.

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

Always use conversation history when supplied.

Understand short follow-up messages from context.

If the user says "give me an example", give an example of the current topic.

If the user says "another one", give a different example.

If the user says "solve it", solve the most recent relevant problem.

If the user says "why", explain the previous statement.

If the user says "make it easier", simplify the previous answer.

If the user says "continue" or "go on", continue the current topic.

For mathematics and physics:
- Explain clearly.
- Give formulas when useful.
- Define variables when useful.
- Show reasoning.
- Give examples when requested.
- Solve step by step when requested.

For education:
- Explain before giving examples when appropriate.
- Do not give an exercise answer unless requested.
- Correct mistakes politely.

For business:
- Give practical recommendations.
- Consider African and Cameroonian realities where relevant.
- Do not invent prices, statistics or regulations.

Do not claim to have performed an action that you did not perform.

Be accurate, natural, helpful and conversational.
"""


# =========================================================
# SUPABASE GENERIC HELPERS
# =========================================================

def supabase_get(url, params):
    return requests.get(
        url,
        headers=supabase_headers(),
        params=params,
        timeout=15
    )


def supabase_insert(url, data):
    return requests.post(
        url,
        headers=supabase_headers("return=representation"),
        json=data,
        timeout=15
    )


def supabase_update(url, params, data):
    return requests.patch(
        url,
        headers=supabase_headers("return=representation"),
        params=params,
        json=data,
        timeout=15
    )


def supabase_delete(url, params):
    return requests.delete(
        url,
        headers=supabase_headers(),
        params=params,
        timeout=15
    )


def first_row(response):
    try:
        data = response.json()
    except Exception:
        return None

    if isinstance(data, list) and data:
        return data[0]

    return None


# =========================================================
# AI CONVERSATION SAVE
# =========================================================

def save_ai_conversation(
    user_id,
    question,
    answer
):

    if not user_id:
        return False

    data = {
        "user_id": user_id,
        "question": question,
        "answer": answer,
        "created_at": now_iso()
    }

    try:

        response = supabase_insert(
            AI_CONVERSATIONS_URL,
            data
        )

        print(
            "AI conversation SAVE:",
            response.status_code,
            response.text
        )

        return response.status_code in (
            200,
            201
        )

    except Exception as error:

        print(
            "AI conversation SAVE exception:",
            error
        )

        traceback.print_exc()

        return False


# =========================================================
# OPENROUTER SINGLE MODEL REQUEST
# =========================================================

def call_openrouter_model(
    model,
    messages,
    title="NexaFlow AI"
):

    if not OPENROUTER_API_KEY:

        return None, {
            "type": "configuration",
            "message": "OPENROUTER_API_KEY is not configured.",
            "status_code": None,
            "model": model
        }

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    headers = {
        "Authorization":
            "Bearer " + OPENROUTER_API_KEY,

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            SUPABASE_PROJECT_URL,

        "X-Title":
            title
    }

    payload = {
        "model": model,
        "messages": messages
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=90
        )

        print(
            "================================================"
        )

        print(
            "OpenRouter model:",
            model
        )

        print(
            "OpenRouter status:",
            response.status_code
        )

        print(
            "================================================"
        )

        try:
            result = response.json()
        except Exception:
            result = {
                "raw_response":
                    response.text
            }

        if response.status_code != 200:

            error_message = (
                result.get("error", {})
                if isinstance(result, dict)
                else result
            )

            print(
                "OpenRouter ERROR:",
                error_message
            )

            return None, {
                "type": "openrouter",
                "message": str(error_message),
                "status_code": response.status_code,
                "model": model,
                "raw": result
            }

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            return None, {
                "type": "empty_response",
                "message":
                    "No AI response was returned.",
                "status_code":
                    response.status_code,
                "model":
                    model
            }

        answer = str(
            choices[0]
            .get("message", {})
            .get("content", "")
        ).strip()

        if not answer:

            return None, {
                "type": "empty_response",
                "message":
                    "AI returned an empty response.",
                "status_code":
                    response.status_code,
                "model":
                    model
            }

        return answer, None

    except requests.exceptions.Timeout:

        print(
            "OpenRouter TIMEOUT:",
            model
        )

        return None, {
            "type": "timeout",
            "message":
                "OpenRouter request timed out.",
            "status_code":
                None,
            "model":
                model
        }

    except requests.exceptions.RequestException as error:

        print(
            "OpenRouter REQUEST ERROR:",
            model,
            error
        )

        traceback.print_exc()

        return None, {
            "type": "request_exception",
            "message":
                str(error),
            "status_code":
                None,
            "model":
                model
        }

    except Exception as error:

        print(
            "OpenRouter EXCEPTION:",
            model,
            error
        )

        traceback.print_exc()

        return None, {
            "type": "exception",
            "message":
                str(error),
            "status_code":
                None,
            "model":
                model
        }


# =========================================================
# OPENROUTER AI WITH AUTOMATIC FREE FALLBACK
# =========================================================

def call_openrouter(
    messages,
    title="NexaFlow AI"
):

    models_to_try = [
        OPENROUTER_PRIMARY_MODEL,
        OPENROUTER_FREE_ROUTER_MODEL
    ]

    last_error = None

    for index, model in enumerate(
        models_to_try
    ):

        print(
            "AI MODEL ATTEMPT:",
            index + 1,
            "of",
            len(models_to_try),
            model
        )

        answer, error = call_openrouter_model(
            model,
            messages,
            title
        )

        if answer:

            print(
                "AI MODEL SUCCESS:",
                model
            )

            return answer, None

        last_error = error or {
            "type": "unknown",
            "message":
                "Unknown OpenRouter error.",
            "status_code":
                None,
            "model":
                model
        }

        status_code = last_error.get(
            "status_code"
        )

        if index == 0:

            print(
                "Primary free model failed.",
                "Status:",
                status_code
            )

            print(
                "Trying OpenRouter free-model router..."
            )

            time.sleep(0.5)

            continue

        break

    print(
        "================================================"
    )

    print(
        "ALL OPENROUTER AI MODELS FAILED"
    )

    print(
        "Last error:",
        last_error
    )

    print(
        "================================================"
    )

    return None, last_error


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

    user = get_authenticated_user()

    user_id = (
        user.get("id")
        if user
        else None
    )

    messages = [{
        "role":
            "system",
        "content":
            NEXAFLOW_SYSTEM_PROMPT
    }]

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

    if len(messages) > 21:

        messages = (
            [messages[0]]
            + messages[-20:]
        )

    answer, error = call_openrouter(
        messages,
        "NexaFlow AI"
    )

    if not answer:

        print(
            "FINAL AI ASSISTANT ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "answer":
                "NexaFlow AI is temporarily unable to respond. "
                "Please try again in a moment.",
            "error":
                "AI service temporarily unavailable."
        }), 503

    saved = save_ai_conversation(
        user_id,
        question,
        answer
    )

    return jsonify({
        "success":
            True,
        "answer":
            answer,
        "conversation_saved":
            saved
    })


# =========================================================
# CUSTOMERS - GET
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

        response = supabase_get(
            CUSTOMERS_URL,
            {
                "select":
                    "*",
                "user_id":
                    "eq." + user["id"],
                "order":
                    "created_at.desc"
            }
        )

        if response.status_code != 200:

            return jsonify({
                "error":
                    "Unable to load customers: "
                    + response.text
            }), response.status_code

        customers = response.json()

        return jsonify({
            "success":
                True,
            "customers":
                customers,
            "count":
                len(customers)
        })

    except Exception as error:

        print(
            "Customers GET exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                "Unable to load customers: "
                + str(error)
        }), 500


# =========================================================
# CUSTOMERS - ADD
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
            data.get(
                "customer_name",
                ""
            )
        )
    ).strip()

    if not name:

        return jsonify({
            "error":
                "Customer name is required."
        }), 400

    customer_data = {
        "user_id":
            user["id"],

        "name":
            name,

        "phone":
            str(
                data.get(
                    "phone",
                    data.get(
                        "phone_number",
                        ""
                    )
                )
            ).strip(),

        "email":
            str(
                data.get(
                    "email",
                    ""
                )
            ).strip(),

        "location":
            str(
                data.get(
                    "location",
                    ""
                )
            ).strip(),

        "message":
            str(
                data.get(
                    "message",
                    data.get(
                        "customer_message",
                        ""
                    )
                )
            ).strip(),

        "ai_reply":
            str(
                data.get(
                    "ai_reply",
                    ""
                )
            ).strip(),

        "created_at":
            now_iso()
    }

    try:

        response = supabase_insert(
            CUSTOMERS_URL,
            customer_data
        )

        if response.status_code not in (
            200,
            201
        ):

            return jsonify({
                "success":
                    False,
                "error":
                    "Unable to save customer: "
                    + response.text
            }), response.status_code

        saved = (
            first_row(response)
            or customer_data
        )

        return jsonify({
            "success":
                True,
            "customer":
                saved,
            "message":
                "Customer saved successfully."
        })

    except Exception as error:

        print(
            "Customer SAVE exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "success":
                False,
            "error":
                str(error)
        }), 500


# =========================================================
# UPDATE CUSTOMER FROM WHATSAPP
# =========================================================

def update_customer_whatsapp_message(
    user_id,
    customer_id,
    message_text
):

    if (
        not user_id
        or not customer_id
        or not message_text
    ):
        return False

    try:

        params = {
            "id":
                "eq." + str(
                    customer_id
                ),

            "user_id":
                "eq." + str(
                    user_id
                )
        }

        data = {
            "message":
                message_text,

            "updated_at":
                now_iso()
        }

        response = supabase_update(
            CUSTOMERS_URL,
            params,
            data
        )

        print(
            "CUSTOMER INCOMING MESSAGE UPDATE:",
            response.status_code,
            response.text
        )

        return response.status_code in (
            200,
            204
        )

    except Exception as error:

        print(
            "Customer WhatsApp message update exception:",
            error
        )

        traceback.print_exc()

        return False


# =========================================================
# UPDATE CUSTOMER AI REPLY
# =========================================================

def update_customer_ai_reply(
    user_id,
    customer_id,
    ai_reply
):

    if (
        not user_id
        or not customer_id
        or not ai_reply
    ):
        return False

    try:

        params = {
            "id":
                "eq." + str(
                    customer_id
                ),

            "user_id":
                "eq." + str(
                    user_id
                )
        }

        data = {
            "ai_reply":
                ai_reply,

            "updated_at":
                now_iso()
        }

        response = supabase_update(
            CUSTOMERS_URL,
            params,
            data
        )

        print(
            "CUSTOMER AI REPLY UPDATE:",
            response.status_code,
            response.text
        )

        return response.status_code in (
            200,
            204
        )

    except Exception as error:

        print(
            "Customer AI reply update exception:",
            error
        )

        traceback.print_exc()

        return False


# =========================================================
# CUSTOMERS - DELETE
# =========================================================

@app.route(
    "/api/customers/<int:customer_id>",
    methods=["DELETE"]
)
def delete_customer(customer_id):

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    try:

        response = supabase_delete(
            CUSTOMERS_URL,
            {
                "id":
                    "eq." + str(
                        customer_id
                    ),

                "user_id":
                    "eq." + user["id"]
            }
        )

        if response.status_code not in (
            200,
            204
        ):

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        return jsonify({
            "success":
                True,
            "message":
                "Customer deleted successfully."
        })

    except Exception as error:

        print(
            "Customer DELETE exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# DASHBOARD
# =========================================================

@app.route(
    "/api/dashboard/stats",
    methods=["GET"]
)
def dashboard_stats():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    user_id = user["id"]

    try:

        customers_response = supabase_get(
            CUSTOMERS_URL,
            {
                "select":
                    "id",
                "user_id":
                    "eq." + user_id
            }
        )

        conversations_response = supabase_get(
            AI_CONVERSATIONS_URL,
            {
                "select":
                    "id",
                "user_id":
                    "eq." + user_id
            }
        )

        business_response = supabase_get(
            BUSINESS_ACCOUNTS_URL,
            {
                "select":
                    "id",
                "user_id":
                    "eq." + user_id,
                "limit":
                    "1"
            }
        )

        messages_response = supabase_get(
            MESSAGES_URL,
            {
                "select":
                    "id,direction,status",
                "user_id":
                    "eq." + user_id,
                "platform":
                    "eq.whatsapp"
            }
        )

        customers = (
            customers_response.json()
            if customers_response.status_code == 200
            else []
        )

        conversations = (
            conversations_response.json()
            if conversations_response.status_code == 200
            else []
        )

        businesses = (
            business_response.json()
            if business_response.status_code == 200
            else []
        )

        whatsapp_messages = (
            messages_response.json()
            if messages_response.status_code == 200
            else []
        )

        incoming = len([
            x
            for x in whatsapp_messages
            if x.get("direction")
            == "inbound"
        ])

        outgoing = len([
            x
            for x in whatsapp_messages
            if x.get("direction")
            == "outbound"
        ])

        return jsonify({
            "success":
                True,

            "stats": {

                "customers":
                    len(customers),

                "ai_conversations":
                    len(conversations),

                "whatsapp_messages":
                    len(whatsapp_messages),

                "whatsapp_incoming":
                    incoming,

                "whatsapp_outgoing":
                    outgoing,

                "reports":
                    len(customers)
                    + len(conversations),

                "business_account":
                    1 if businesses
                    else 0
            }
        })

    except Exception as error:

        print(
            "Dashboard stats exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# AI CONVERSATIONS
# =========================================================

@app.route(
    "/api/ai/conversations",
    methods=["GET"]
)
def get_ai_conversations():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    try:

        response = supabase_get(
            AI_CONVERSATIONS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user["id"],

                "order":
                    "created_at.desc"
            }
        )

        if response.status_code != 200:

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        conversations = response.json()

        return jsonify({
            "success":
                True,

            "conversations":
                conversations,

            "count":
                len(conversations)
        })

    except Exception as error:

        print(
            "AI conversations GET exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# AUTOMATION
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

        response = supabase_get(
            AUTOMATION_SETTINGS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user["id"],

                "limit":
                    "1"
            }
        )

        if response.status_code != 200:

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        rows = response.json()

        if rows:

            return jsonify({
                "automation":
                    rows[0]
            })

        return jsonify({
            "automation": {
                "user_id":
                    user["id"],

                "ai_replies":
                    True,

                "message_automation":
                    True,

                "task_automation":
                    True
            }
        })

    except Exception as error:

        print(
            "Automation GET exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


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

    settings = {

        "user_id":
            user["id"],

        "ai_replies":
            bool(
                data.get(
                    "ai_replies",
                    True
                )
            ),

        "message_automation":
            bool(
                data.get(
                    "message_automation",
                    True
                )
            ),

        "task_automation":
            bool(
                data.get(
                    "task_automation",
                    True
                )
            ),

        "updated_at":
            now_iso()
    }

    try:

        existing_response = supabase_get(
            AUTOMATION_SETTINGS_URL,
            {
                "select":
                    "id",

                "user_id":
                    "eq." + user["id"],

                "limit":
                    "1"
            }
        )

        existing = (
            existing_response.json()
            if existing_response.status_code == 200
            else []
        )

        if existing:

            response = supabase_update(
                AUTOMATION_SETTINGS_URL,
                {
                    "user_id":
                        "eq." + user["id"]
                },
                settings
            )

        else:

            response = supabase_insert(
                AUTOMATION_SETTINGS_URL,
                settings
            )

        if response.status_code not in (
            200,
            201,
            204
        ):

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        return jsonify({
            "success":
                True,

            "automation":
                first_row(response)
                or settings,

            "message":
                "Automation settings saved successfully."
        })

    except Exception as error:

        print(
            "Automation SAVE exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


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

    allowed = {
        "ai_replies",
        "message_automation",
        "task_automation"
    }

    if setting not in allowed:

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

    try:

        check = supabase_get(
            AUTOMATION_SETTINGS_URL,
            {
                "select":
                    "id",

                "user_id":
                    "eq." + user["id"],

                "limit":
                    "1"
            }
        )

        existing = (
            check.json()
            if check.status_code == 200
            else []
        )

        if existing:

            response = supabase_update(
                AUTOMATION_SETTINGS_URL,
                {
                    "user_id":
                        "eq." + user["id"]
                },
                {
                    setting:
                        value,

                    "updated_at":
                        now_iso()
                }
            )

        else:

            settings = {

                "user_id":
                    user["id"],

                "ai_replies":
                    True,

                "message_automation":
                    True,

                "task_automation":
                    True,

                "updated_at":
                    now_iso()
            }

            settings[setting] = value

            response = supabase_insert(
                AUTOMATION_SETTINGS_URL,
                settings
            )

        if response.status_code not in (
            200,
            201,
            204
        ):

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        return jsonify({
            "success":
                True,

            "setting":
                setting,

            "value":
                value,

            "automation":
                first_row(response)
        })

    except Exception as error:

        print(
            "Automation toggle exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# BUSINESS
# =========================================================

@app.route(
    "/api/business",
    methods=["GET", "POST"]
)
def business_account():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    user_id = user["id"]

    if request.method == "GET":

        try:

            response = supabase_get(
                BUSINESS_ACCOUNTS_URL,
                {
                    "select":
                        "*",

                    "user_id":
                        "eq." + user_id,

                    "limit":
                        "1"
                }
            )

            if response.status_code != 200:

                return jsonify({
                    "error":
                        response.text
                }), response.status_code

            rows = response.json()

            return jsonify({
                "business":
                    rows[0]
                    if rows
                    else None
            })

        except Exception as error:

            print(
                "Business GET exception:",
                error
            )

            traceback.print_exc()

            return jsonify({
                "error":
                    str(error)
            }), 500

    data = request.get_json(
        silent=True
    ) or {}

    business_data = {

        "user_id":
            user_id,

        "business_name":
            str(
                data.get(
                    "business_name",
                    ""
                )
            ).strip(),

        "owner_name":
            str(
                data.get(
                    "owner_name",
                    ""
                )
            ).strip(),

        "phone":
            str(
                data.get(
                    "phone",
                    ""
                )
            ).strip(),

        "email":
            str(
                data.get(
                    "email",
                    ""
                )
            ).strip(),

        "address":
            str(
                data.get(
                    "address",
                    ""
                )
            ).strip(),

        "description":
            str(
                data.get(
                    "description",
                    ""
                )
            ).strip(),

        "logo":
            str(
                data.get(
                    "logo",
                    ""
                )
            ).strip(),

        "updated_at":
            now_iso()
    }

    try:

        check = supabase_get(
            BUSINESS_ACCOUNTS_URL,
            {
                "select":
                    "id",

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"
            }
        )

        existing = (
            check.json()
            if check.status_code == 200
            else []
        )

        if existing:

            response = supabase_update(
                BUSINESS_ACCOUNTS_URL,
                {
                    "id":
                        "eq." + str(
                            existing[0]["id"]
                        ),

                    "user_id":
                        "eq." + user_id
                },
                business_data
            )

        else:

            response = supabase_insert(
                BUSINESS_ACCOUNTS_URL,
                business_data
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
            "success":
                True,

            "business":
                first_row(response)
                or business_data,

            "message":
                "Business settings saved successfully."
        })

    except Exception as error:

        print(
            "Business SAVE exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# BUSINESS LOGO
# =========================================================

@app.route(
    "/api/business/logo",
    methods=["POST"]
)
def upload_business_logo():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    if "logo" not in request.files:

        return jsonify({
            "error":
                "No logo file was provided."
        }), 400

    logo_file = request.files["logo"]

    if not logo_file.filename:

        return jsonify({
            "error":
                "No logo file was selected."
        }), 400

    allowed = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp"
    )

    if not logo_file.filename.lower().endswith(
        allowed
    ):

        return jsonify({
            "error":
                "Unsupported logo format."
        }), 400

    try:

        file_bytes = logo_file.read()

        if not file_bytes:

            return jsonify({
                "error":
                    "The selected logo file is empty."
            }), 400

        bucket = "business-logos"

        extension = os.path.splitext(
            logo_file.filename
        )[1].lower()

        path = (
            user["id"]
            + "/business-logo"
            + extension
        )

        storage_url = (
            SUPABASE_PROJECT_URL
            + "/storage/v1/object/"
            + bucket
            + "/"
            + path
        )

        response = requests.post(
            storage_url,
            headers={
                "Authorization":
                    "Bearer "
                    + str(
                        SUPABASE_SECRET_KEY
                    ),

                "apikey":
                    SUPABASE_SECRET_KEY,

                "Content-Type":
                    logo_file.content_type
                    or
                    "application/octet-stream",

                "x-upsert":
                    "true"
            },
            data=file_bytes,
            timeout=30
        )

        if response.status_code not in (
            200,
            201
        ):

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        logo_url = (
            SUPABASE_PROJECT_URL
            + "/storage/v1/object/public/"
            + bucket
            + "/"
            + path
        )

        return jsonify({
            "success":
                True,

            "logo":
                logo_url,

            "message":
                "Business logo uploaded successfully."
        })

    except Exception as error:

        print(
            "Business logo upload exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# WHATSAPP INTEGRATIONS
# =========================================================

@app.route(
    "/api/integrations",
    methods=["GET"]
)
def get_integrations():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    try:

        response = supabase_get(
            INTEGRATIONS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user["id"],

                "order":
                    "created_at.desc"
            }
        )

        if response.status_code != 200:

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        rows = response.json()

        return jsonify({
            "success":
                True,

            "integrations":
                rows,

            "count":
                len(rows)
        })

    except Exception as error:

        print(
            "Integrations GET exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


@app.route(
    "/api/integrations",
    methods=["POST"]
)
def save_integration():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    platform = str(
        data.get(
            "platform",
            "whatsapp"
        )
    ).strip().lower()

    if platform != "whatsapp":

        return jsonify({
            "error":
                "This endpoint currently supports WhatsApp only."
        }), 400

    account_name = str(
        data.get(
            "account_name",
            ""
        )
    ).strip()

    account_id = str(
        data.get(
            "account_id",
            WHATSAPP_BUSINESS_ACCOUNT_ID
            or ""
        )
    ).strip()

    access_token = str(
        data.get(
            "access_token",
            WHATSAPP_ACCESS_TOKEN
            or ""
        )
    ).strip()

    phone_number = str(
        data.get(
            "phone_number",
            ""
        )
    ).strip()

    phone_number_id = str(
        data.get(
            "phone_number_id",
            WHATSAPP_PHONE_NUMBER_ID
            or ""
        )
    ).strip()

    if not phone_number_id:

        return jsonify({
            "error":
                "WhatsApp phone number ID is required."
        }), 400

    integration = {

        "user_id":
            user["id"],

        "platform":
            "whatsapp",

        "account_name":
            account_name,

        "account_id":
            account_id,

        "access_token":
            access_token,

        "phone_number":
            phone_number,

        "status":
            "connected",

        "settings": {
            "phone_number_id":
                phone_number_id
        },

        "connected_at":
            now_iso(),

        "updated_at":
            now_iso()
    }

    try:

        check = supabase_get(
            INTEGRATIONS_URL,
            {
                "select":
                    "id",

                "user_id":
                    "eq." + user["id"],

                "platform":
                    "eq.whatsapp",

                "account_id":
                    "eq." + account_id,

                "limit":
                    "1"
            }
        )

        existing = (
            check.json()
            if check.status_code == 200
            else []
        )

        if existing:

            response = supabase_update(
                INTEGRATIONS_URL,
                {
                    "id":
                        "eq." + str(
                            existing[0]["id"]
                        ),

                    "user_id":
                        "eq." + user["id"]
                },
                integration
            )

        else:

            response = supabase_insert(
                INTEGRATIONS_URL,
                integration
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
            "success":
                True,

            "integration":
                first_row(response)
                or integration,

            "message":
                "WhatsApp integration saved successfully."
        })

    except Exception as error:

        print(
            "Integration SAVE exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


@app.route(
    "/api/integrations/<int:integration_id>",
    methods=["DELETE"]
)
def delete_integration(integration_id):

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    try:

        response = supabase_delete(
            INTEGRATIONS_URL,
            {
                "id":
                    "eq." + str(
                        integration_id
                    ),

                "user_id":
                    "eq." + user["id"]
            }
        )

        if response.status_code not in (
            200,
            204
        ):

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        return jsonify({
            "success":
                True,

            "message":
                "Integration deleted successfully."
        })

    except Exception as error:

        print(
            "Integration DELETE exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# WHATSAPP FIND INTEGRATION
# =========================================================

def find_whatsapp_integration(
    phone_number_id
):

    print(
        "========== WHATSAPP INTEGRATION LOOKUP =========="
    )

    print(
        "Incoming phone_number_id:",
        phone_number_id
    )

    if not phone_number_id:
        return None

    try:

        response = supabase_get(
            INTEGRATIONS_URL,
            {
                "select":
                    "*",

                "platform":
                    "eq.whatsapp"
            }
        )

        print(
            "Integration lookup status:",
            response.status_code
        )

        print(
            "Integration lookup response:",
            response.text
        )

        if response.status_code != 200:
            return None

        integrations = response.json()

        for integration in integrations:

            settings = (
                integration.get(
                    "settings"
                )
                or {}
            )

            stored_phone_id = str(
                settings.get(
                    "phone_number_id",
                    ""
                )
            ).strip()

            print(
                "Checking integration:",
                integration.get("id"),
                "stored phone ID:",
                stored_phone_id
            )

            if stored_phone_id == str(
                phone_number_id
            ).strip():

                print(
                    "========== MATCH FOUND =========="
                )

                print(
                    "Integration ID:",
                    integration.get("id")
                )

                print(
                    "User ID:",
                    integration.get("user_id")
                )

                return integration

        print(
            "========== NO MATCH FOUND =========="
        )

        return None

    except Exception as error:

        print(
            "Integration lookup exception:",
            error
        )

        traceback.print_exc()

        return None


# =========================================================
# WHATSAPP FIND / CREATE CUSTOMER
# =========================================================

def find_or_create_whatsapp_customer(
    user_id,
    phone,
    name=""
):

    if not user_id or not phone:
        return None

    phone = str(
        phone
    ).strip()

    try:

        response = supabase_get(
            CUSTOMERS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "phone":
                    "eq." + phone,

                "limit":
                    "1"
            }
        )

        print(
            "WhatsApp customer lookup:",
            response.status_code,
            response.text
        )

        if response.status_code != 200:
            return None

        customers = response.json()

        if customers:
            return customers[0]

        customer_data = {

            "user_id":
                user_id,

            "name":
                name or phone,

            "phone":
                phone,

            "email":
                "",

            "location":
                "",

            "message":
                "",

            "ai_reply":
                "",

            "created_at":
                now_iso()
        }

        create_response = supabase_insert(
            CUSTOMERS_URL,
            customer_data
        )

        print(
            "WhatsApp customer CREATE:",
            create_response.status_code,
            create_response.text
        )

        if create_response.status_code not in (
            200,
            201
        ):
            return None

        return (
            first_row(
                create_response
            )
            or customer_data
        )

    except Exception as error:

        print(
            "WhatsApp customer exception:",
            error
        )

        traceback.print_exc()

        return None


# =========================================================
# WHATSAPP DUPLICATE CHECK
# =========================================================

def whatsapp_message_exists(
    external_message_id
):

    if not external_message_id:
        return False

    try:

        response = supabase_get(
            MESSAGES_URL,
            {
                "select":
                    "id",

                "external_message_id":
                    "eq." + external_message_id,

                "limit":
                    "1"
            }
        )

        if response.status_code != 200:
            return False

        return bool(
            response.json()
        )

    except Exception as error:

        print(
            "WhatsApp duplicate check exception:",
            error
        )

        return False


# =========================================================
# WHATSAPP STORE INCOMING
# =========================================================

def store_whatsapp_message(
    integration,
    sender_phone,
    sender_name,
    message_text,
    external_message_id
):

    if not integration:
        return None

    user_id = integration.get(
        "user_id"
    )

    customer = find_or_create_whatsapp_customer(
        user_id,
        sender_phone,
        sender_name
    )

    customer_id = (
        customer.get("id")
        if customer
        else None
    )

    if customer_id and message_text:

        updated = update_customer_whatsapp_message(
            user_id,
            customer_id,
            message_text
        )

        print(
            "Customer message field updated:",
            updated
        )

    message_data = {

        "user_id":
            user_id,

        "integration_id":
            integration.get("id"),

        "customer_id":
            customer_id,

        "platform":
            "whatsapp",

        "external_message_id":
            external_message_id
            or "",

        "direction":
            "inbound",

        "sender_name":
            sender_name
            or "",

        "sender_phone":
            sender_phone
            or "",

        "message":
            message_text
            or "",

        "ai_generated":
            False,

        "ai_reply":
            "",

        "status":
            "received",

        "metadata": {
            "source":
                "whatsapp_webhook"
        },

        "created_at":
            now_iso(),

        "updated_at":
            now_iso()
    }

    try:

        response = supabase_insert(
            MESSAGES_URL,
            message_data
        )

        print(
            "WhatsApp message SAVE:",
            response.status_code,
            response.text
        )

        if response.status_code not in (
            200,
            201
        ):
            return None

        return (
            first_row(
                response
            )
            or message_data
        )

    except Exception as error:

        print(
            "WhatsApp message SAVE exception:",
            error
        )

        traceback.print_exc()

        return None


# =========================================================
# WHATSAPP MESSAGES GET
# =========================================================

@app.route(
    "/api/messages",
    methods=["GET"]
)
def get_messages():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    customer_id = request.args.get(
        "customer_id",
        ""
    ).strip()

    try:

        limit = int(
            request.args.get(
                "limit",
                "100"
            )
        )

    except ValueError:

        limit = 100

    limit = max(
        1,
        min(
            limit,
            500
        )
    )

    params = {

        "select":
            "*",

        "user_id":
            "eq." + user["id"],

        "platform":
            "eq.whatsapp",

        "order":
            "created_at.desc",

        "limit":
            str(limit)
    }

    if customer_id:

        params["customer_id"] = (
            "eq." + customer_id
        )

    try:

        response = supabase_get(
            MESSAGES_URL,
            params
        )

        if response.status_code != 200:

            return jsonify({
                "success":
                    False,

                "error":
                    response.text
            }), response.status_code

        messages = response.json()

        return jsonify({
            "success":
                True,

            "messages":
                messages,

            "count":
                len(messages)
        })

    except Exception as error:

        print(
            "Messages GET exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "success":
                False,

            "error":
                str(error)
        }), 500


# =========================================================
# WHATSAPP CONVERSATION
# =========================================================

@app.route(
    "/api/messages/conversation/<int:customer_id>",
    methods=["GET"]
)
def get_whatsapp_customer_conversation(
    customer_id
):

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    user_id = user["id"]

    try:

        customer_response = supabase_get(
            CUSTOMERS_URL,
            {
                "select":
                    "*",

                "id":
                    "eq." + str(
                        customer_id
                    ),

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"
            }
        )

        if customer_response.status_code != 200:

            return jsonify({
                "error":
                    customer_response.text
            }), customer_response.status_code

        customers = customer_response.json()

        if not customers:

            return jsonify({
                "error":
                    "Customer not found."
            }), 404

        message_response = supabase_get(
            MESSAGES_URL,
            {
                "select":
                    "*",

                "customer_id":
                    "eq." + str(
                        customer_id
                    ),

                "user_id":
                    "eq." + user_id,

                "platform":
                    "eq.whatsapp",

                "order":
                    "created_at.asc"
            }
        )

        if message_response.status_code != 200:

            return jsonify({
                "error":
                    message_response.text
            }), message_response.status_code

        messages = message_response.json()

        return jsonify({

            "success":
                True,

            "customer":
                customers[0],

            "messages":
                messages,

            "count":
                len(messages)
        })

    except Exception as error:

        print(
            "WhatsApp conversation GET exception:",
            error
        )

        traceback.print_exc()

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# WHATSAPP AUTOMATION CHECK
# =========================================================

def whatsapp_automation_enabled(
    user_id
):

    try:

        response = supabase_get(
            AUTOMATION_SETTINGS_URL,
            {
                "select":
                    "ai_replies,message_automation",

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"
            }
        )

        if response.status_code != 200:
            return False

        rows = response.json()

        if not rows:
            return True

        settings = rows[0]

        return bool(
            settings.get(
                "ai_replies",
                True
            )
            and
            settings.get(
                "message_automation",
                True
            )
        )

    except Exception as error:

        print(
            "Automation lookup exception:",
            error
        )

        traceback.print_exc()

        return False


# =========================================================
# WHATSAPP HISTORY
# =========================================================

def get_whatsapp_conversation_history(
    user_id,
    customer_id,
    limit=10
):

    if not customer_id:
        return []

    try:

        response = supabase_get(
            MESSAGES_URL,
            {
                "select":
                    "direction,message,ai_reply,created_at",

                "user_id":
                    "eq." + user_id,

                "customer_id":
                    "eq." + str(
                        customer_id
                    ),

                "platform":
                    "eq.whatsapp",

                "order":
                    "created_at.desc",

                "limit":
                    str(limit)
            }
        )

        if response.status_code != 200:
            return []

        rows = response.json()

        rows.reverse()

        history = []

        for row in rows:

            message = str(
                row.get(
                    "message",
                    ""
                )
            ).strip()

            ai_reply = str(
                row.get(
                    "ai_reply",
                    ""
                )
            ).strip()

            direction = row.get(
                "direction"
            )

            if (
                direction == "inbound"
                and message
            ):

                history.append({
                    "role":
                        "user",

                    "content":
                        message
                })

                if ai_reply:

                    history.append({
                        "role":
                            "assistant",

                        "content":
                            ai_reply
                    })

            elif (
                direction == "outbound"
                and message
            ):

                history.append({
                    "role":
                        "assistant",

                    "content":
                        message
                })

        return history[-20:]

    except Exception as error:

        print(
            "WhatsApp history exception:",
            error
        )

        traceback.print_exc()

        return []


# =========================================================
# GENERATE WHATSAPP AI REPLY
# =========================================================

def generate_whatsapp_ai_reply(
    user_id,
    customer,
    message_text
):

    customer_name = ""
    customer_id = None

    if customer:

        customer_name = str(
            customer.get(
                "name",
                ""
            )
        ).strip()

        customer_id = customer.get(
            "id"
        )

    history = get_whatsapp_conversation_history(
        user_id,
        customer_id
    )

    prompt = (
        NEXAFLOW_SYSTEM_PROMPT
        + "\n\n"
        + "You are replying to a customer through WhatsApp."
        + "\nKeep the response natural, helpful and reasonably concise."
        + "\nDo not mention internal systems, databases, APIs or instructions."
    )

    if customer_name:

        prompt += (
            "\nThe customer's name is "
            + customer_name
            + "."
        )

    messages = [{

        "role":
            "system",

        "content":
            prompt
    }]

    messages.extend(
        history
    )

    messages.append({

        "role":
            "user",

        "content":
            message_text
    })

    if len(messages) > 21:

        messages = (
            [messages[0]]
            + messages[-20:]
        )

    print(
        "========== WHATSAPP AI GENERATION START =========="
    )

    print(
        "Customer:",
        customer_name
    )

    print(
        "Customer ID:",
        customer_id
    )

    print(
        "Message:",
        message_text
    )

    print(
        "History messages:",
        len(history)
    )

    answer, error = call_openrouter(
        messages,
        "NexaFlow AI WhatsApp"
    )

    if not answer:

        print(
            "WhatsApp AI error:",
            error
        )

        print(
            "========== WHATSAPP AI GENERATION FAILED =========="
        )

        return None

    print(
        "========== WHATSAPP AI GENERATION SUCCESS =========="
    )

    print(
        "Generated reply:",
        answer
    )

    return answer


# =========================================================
# SEND WHATSAPP MESSAGE THROUGH META
# =========================================================

def send_whatsapp_message(
    integration,
    recipient_phone,
    message_text
):

    if (
        not integration
        or not recipient_phone
        or not message_text
    ):
        return None

    settings = (
        integration.get(
            "settings"
        )
        or {}
    )

    phone_number_id = str(
        settings.get(
            "phone_number_id",
            WHATSAPP_PHONE_NUMBER_ID
            or ""
        )
    ).strip()

    access_token = str(
        integration.get(
            "access_token",
            WHATSAPP_ACCESS_TOKEN
            or ""
        )
    ).strip()

    if not phone_number_id:

        print(
            "WhatsApp send error: phone number ID missing."
        )

        return None

    if not access_token:

        print(
            "WhatsApp send error: access token missing."
        )

        return None

    url = (
        "https://graph.facebook.com/v23.0/"
        + phone_number_id
        + "/messages"
    )

    print(
        "========== WHATSAPP META SEND START =========="
    )

    print(
        "Recipient:",
        recipient_phone
    )

    print(
        "Phone number ID:",
        phone_number_id
    )

    print(
        "Message length:",
        len(message_text)
    )

    try:

        response = requests.post(
            url,
            headers={
                "Authorization":
                    "Bearer "
                    + access_token,

                "Content-Type":
                    "application/json"
            },

            json={

                "messaging_product":
                    "whatsapp",

                "to":
                    recipient_phone,

                "type":
                    "text",

                "text": {

                    "preview_url":
                        False,

                    "body":
                        message_text
                }
            },

            timeout=30
        )

        print(
            "WhatsApp SEND:",
            response.status_code,
            response.text
        )

        if response.status_code not in (
            200,
            201
        ):

            print(
                "========== WHATSAPP META SEND FAILED =========="
            )

            return None

        print(
            "========== WHATSAPP META SEND SUCCESS =========="
        )

        return response.json()

    except Exception as error:

        print(
            "WhatsApp SEND exception:",
            error
        )

        traceback.print_exc()

        return None


# =========================================================
# STORE OUTGOING WHATSAPP MESSAGE
# =========================================================

def store_whatsapp_outgoing_message(
    integration,
    customer,
    recipient_phone,
    message_text,
    whatsapp_response
):

    if not integration:
        return None

    user_id = integration.get(
        "user_id"
    )

    customer_id = (
        customer.get("id")
        if customer
        else None
    )

    response_messages = (
        whatsapp_response.get(
            "messages",
            []
        )
        if isinstance(
            whatsapp_response,
            dict
        )
        else []
    )

    external_message_id = ""

    if response_messages:

        external_message_id = str(
            response_messages[0].get(
                "id",
                ""
            )
        )

    data = {

        "user_id":
            user_id,

        "integration_id":
            integration.get("id"),

        "customer_id":
            customer_id,

        "platform":
            "whatsapp",

        "external_message_id":
            external_message_id,

        "direction":
            "outbound",

        "sender_name":
            "NexaFlow AI",

        "sender_phone":
            recipient_phone,

        "message":
            message_text,

        "ai_generated":
            True,

        "ai_reply":
            message_text,

        "status":
            "sent",

        "metadata": {
            "source":
                "nexaflow_ai"
        },

        "created_at":
            now_iso(),

        "updated_at":
            now_iso()
    }

    try:

        response = supabase_insert(
            MESSAGES_URL,
            data
        )

        print(
            "Outgoing WhatsApp SAVE:",
            response.status_code,
            response.text
        )

        if response.status_code not in (
            200,
            201
        ):

            print(
                "Outgoing WhatsApp message failed to save."
            )

            return None

        print(
            "Outgoing WhatsApp message saved successfully."
        )

        return (
            first_row(
                response
            )
            or data
        )

    except Exception as error:

        print(
            "Outgoing WhatsApp SAVE exception:",
            error
        )

        traceback.print_exc()

        return None


# =========================================================
# UPDATE INCOMING MESSAGE
# =========================================================

def update_incoming_message_with_ai_reply(
    message_id,
    ai_reply
):

    if (
        not message_id
        or not ai_reply
    ):
        return False

    try:

        response = supabase_update(
            MESSAGES_URL,
            {
                "id":
                    "eq." + str(
                        message_id
                    )
            },
            {
                "ai_reply":
                    ai_reply,

                "status":
                    "replied",

                "updated_at":
                    now_iso()
            }
        )

        print(
            "Incoming message AI update:",
            response.status_code,
            response.text
        )

        return response.status_code in (
            200,
            204
        )

    except Exception as error:

        print(
            "Incoming message update exception:",
            error
        )

        traceback.print_exc()

        return False


# =========================================================
# PROCESS WHATSAPP AI REPLY
# =========================================================

def process_whatsapp_ai_reply(
    integration,
    stored_message
):

    print(
        "================================================"
    )

    print(
        "BACKGROUND WHATSAPP AI PROCESS STARTED"
    )

    print(
        "================================================"
    )

    try:

        if (
            not integration
            or not stored_message
        ):

            print(
                "Missing integration or stored message."
            )

            return False

        user_id = integration.get(
            "user_id"
        )

        if not user_id:

            print(
                "WhatsApp AI error: integration has no user_id."
            )

            return False

        if not whatsapp_automation_enabled(
            user_id
        ):

            print(
                "WhatsApp AI automation is disabled."
            )

            return False

        message_text = str(
            stored_message.get(
                "message",
                ""
            )
        ).strip()

        recipient_phone = str(
            stored_message.get(
                "sender_phone",
                ""
            )
        ).strip()

        if (
            not message_text
            or not recipient_phone
        ):

            print(
                "WhatsApp AI error: message or recipient phone missing."
            )

            return False

        customer_id = stored_message.get(
            "customer_id"
        )

        customer = None

        if customer_id:

            try:

                response = supabase_get(
                    CUSTOMERS_URL,
                    {
                        "select":
                            "*",

                        "id":
                            "eq." + str(
                                customer_id
                            ),

                        "user_id":
                            "eq." + user_id,

                        "limit":
                            "1"
                    }
                )

                print(
                    "Customer retrieval:",
                    response.status_code,
                    response.text
                )

                if response.status_code == 200:

                    rows = response.json()

                    if rows:
                        customer = rows[0]

            except Exception as error:

                print(
                    "Customer retrieval exception:",
                    error
                )

                traceback.print_exc()

        # -------------------------------------------------
        # GENERATE AI
        # -------------------------------------------------

        print(
            "STEP 1: GENERATING WHATSAPP AI REPLY"
        )

        ai_reply = generate_whatsapp_ai_reply(
            user_id,
            customer,
            message_text
        )

        if not ai_reply:

            print(
                "STEP 1 FAILED: AI did not generate a reply."
            )

            return False

        print(
            "STEP 1 SUCCESS"
        )

        # -------------------------------------------------
        # SEND THROUGH META
        # -------------------------------------------------

        print(
            "STEP 2: SENDING AI REPLY THROUGH META"
        )

        whatsapp_response = send_whatsapp_message(
            integration,
            recipient_phone,
            ai_reply
        )

        if not whatsapp_response:

            print(
                "STEP 2 FAILED: Meta did not send the message."
            )

            return False

        print(
            "STEP 2 SUCCESS"
        )

        # -------------------------------------------------
        # SAVE OUTGOING MESSAGE
        # -------------------------------------------------

        print(
            "STEP 3: SAVING OUTGOING MESSAGE"
        )

        outgoing = store_whatsapp_outgoing_message(
            integration,
            customer,
            recipient_phone,
            ai_reply,
            whatsapp_response
        )

        if not outgoing:

            print(
                "STEP 3 FAILED: outgoing message was not saved."
            )

            return False

        print(
            "STEP 3 SUCCESS"
        )

        # -------------------------------------------------
        # UPDATE INCOMING MESSAGE
        # -------------------------------------------------

        print(
            "STEP 4: UPDATING INCOMING MESSAGE"
        )

        incoming_updated = (
            update_incoming_message_with_ai_reply(
                stored_message.get("id"),
                ai_reply
            )
        )

        print(
            "Incoming message updated:",
            incoming_updated
        )

        # -------------------------------------------------
        # UPDATE CUSTOMER AI REPLY
        # -------------------------------------------------

        if customer_id:

            print(
                "STEP 5: UPDATING CUSTOMER AI REPLY"
            )

            updated = update_customer_ai_reply(
                user_id,
                customer_id,
                ai_reply
            )

            print(
                "Customer ai_reply field updated:",
                updated
            )

        print(
            "================================================"
        )

        print(
            "BACKGROUND WHATSAPP AI PROCESS SUCCESS"
        )

        print(
            "================================================"
        )

        return True

    except Exception as error:

        print(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )

        print(
            "BACKGROUND WHATSAPP AI PROCESS CRASHED"
        )

        print(
            "ERROR:",
            error
        )

        print(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )

        traceback.print_exc()

        return False


# =========================================================
# BACKGROUND WHATSAPP AI THREAD
# =========================================================

def run_whatsapp_ai_background(
    integration,
    stored_message
):

    print(
        "################################################"
    )

    print(
        "STARTING BACKGROUND WHATSAPP AI THREAD"
    )

    print(
        "Message ID:",
        stored_message.get("id")
        if stored_message
        else None
    )

    print(
        "################################################"
    )

    try:

        success = process_whatsapp_ai_reply(
            integration,
            stored_message
        )

        print(
            "BACKGROUND WHATSAPP THREAD FINISHED:",
            success
        )

    except Exception as error:

        print(
            "BACKGROUND WHATSAPP THREAD EXCEPTION:",
            error
        )

        traceback.print_exc()


# =========================================================
# WHATSAPP WEBHOOK VERIFY
# =========================================================

@app.route(
    "/api/whatsapp/webhook",
    methods=["GET"]
)
def whatsapp_webhook_verify():

    mode = request.args.get(
        "hub.mode"
    )

    token = request.args.get(
        "hub.verify_token"
    )

    challenge = request.args.get(
        "hub.challenge"
    )

    if (
        mode == "subscribe"
        and token
        and WHATSAPP_VERIFY_TOKEN
        and token == WHATSAPP_VERIFY_TOKEN
    ):

        print(
            "WhatsApp webhook verification successful."
        )

        return challenge or "", 200

    print(
        "WhatsApp webhook verification failed."
    )

    return "Forbidden", 403


# =========================================================
# WHATSAPP WEBHOOK
# =========================================================

@app.route(
    "/api/whatsapp/webhook",
    methods=["POST"]
)
def whatsapp_webhook():

    print(
        "========== WHATSAPP WEBHOOK START =========="
    )

    payload = request.get_json(
        silent=True
    ) or {}

    print(
        "========== WHATSAPP PAYLOAD =========="
    )

    print(
        payload
    )

    if payload.get(
        "object"
    ) != "whatsapp_business_account":

        print(
            "Webhook object is not WhatsApp Business Account."
        )

        return jsonify({
            "success":
                True
        }), 200

    entries = payload.get(
        "entry",
        []
    )

    processed = 0

    for entry in entries:

        changes = entry.get(
            "changes",
            []
        )

        for change in changes:

            value = change.get(
                "value",
                {}
            )

            metadata = value.get(
                "metadata",
                {}
            )

            phone_number_id = metadata.get(
                "phone_number_id"
            )

            print(
                "META PHONE NUMBER ID:",
                phone_number_id
            )

            integration = find_whatsapp_integration(
                phone_number_id
            )

            if not integration:

                print(
                    "NO INTEGRATION FOUND FOR:",
                    phone_number_id
                )

                continue

            print(
                "MATCHED INTEGRATION:",
                integration.get("id")
            )

            print(
                "MATCHED USER:",
                integration.get("user_id")
            )

            messages = value.get(
                "messages",
                []
            )

            contacts = value.get(
                "contacts",
                []
            )

            contact_name = ""

            if contacts:

                profile = contacts[0].get(
                    "profile",
                    {}
                )

                contact_name = str(
                    profile.get(
                        "name",
                        ""
                    )
                ).strip()

            for incoming in messages:

                external_message_id = incoming.get(
                    "id"
                )

                print(
                    "INCOMING WHATSAPP MESSAGE ID:",
                    external_message_id
                )

                if whatsapp_message_exists(
                    external_message_id
                ):

                    print(
                        "DUPLICATE MESSAGE:",
                        external_message_id
                    )

                    continue

                sender_phone = str(
                    incoming.get(
                        "from",
                        ""
                    )
                ).strip()

                message_type = incoming.get(
                    "type",
                    ""
                )

                message_text = ""

                if message_type == "text":

                    message_text = str(
                        incoming.get(
                            "text",
                            {}
                        ).get(
                            "body",
                            ""
                        )
                    ).strip()

                else:

                    message_text = (
                        "["
                        + str(
                            message_type
                        )
                        + " message]"
                    )

                print(
                    "SENDER:",
                    sender_phone
                )

                print(
                    "CUSTOMER NAME:",
                    contact_name
                )

                print(
                    "MESSAGE TYPE:",
                    message_type
                )

                print(
                    "MESSAGE TEXT:",
                    message_text
                )

                # -------------------------------------------------
                # STORE MESSAGE FIRST
                # -------------------------------------------------

                stored = store_whatsapp_message(
                    integration,
                    sender_phone,
                    contact_name,
                    message_text,
                    external_message_id
                )

                if not stored:

                    print(
                        "FAILED TO STORE INCOMING MESSAGE"
                    )

                    continue

                processed += 1

                print(
                    "STORED MESSAGE:",
                    stored
                )

                # -------------------------------------------------
                # START AI IN BACKGROUND
                # -------------------------------------------------

                print(
                    "STARTING BACKGROUND AI PROCESS FOR MESSAGE:",
                    stored.get("id")
                )

                try:

                    ai_thread = threading.Thread(
                        target=run_whatsapp_ai_background,
                        args=(
                            integration,
                            stored
                        ),
                        daemon=True
                    )

                    ai_thread.start()

                    print(
                        "BACKGROUND AI THREAD STARTED:",
                        ai_thread.name
                    )

                except Exception as error:

                    print(
                        "FAILED TO START BACKGROUND AI THREAD:",
                        error
                    )

                    traceback.print_exc()

    # ---------------------------------------------------------
    # IMPORTANT:
    # RETURN TO META IMMEDIATELY.
    # AI CONTINUES IN THE BACKGROUND THREAD.
    # ---------------------------------------------------------

    print(
        "========== WHATSAPP WEBHOOK END =========="
    )

    print(
        "Returning HTTP 200 to Meta."
    )

    print(
        "Processed messages:",
        processed
    )

    return jsonify({
        "success":
            True,

        "processed":
            processed,

        "message":
            "WhatsApp messages received successfully."
    }), 200


# =========================================================
# REPORTS
# =========================================================

@app.route(
    "/api/reports",
    methods=["GET"]
)
def get_reports():

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    user_id = user["id"]

    try:

        customers_response = supabase_get(
            CUSTOMERS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "order":
                    "created_at.desc"
            }
        )

        ai_response = supabase_get(
            AI_CONVERSATIONS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "order":
                    "created_at.desc"
            }
        )

        business_response = supabase_get(
            BUSINESS_ACCOUNTS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"
            }
        )

        automation_response = supabase_get(
            AUTOMATION_SETTINGS_URL,
            {
                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"
            }
        )

        customers = (
            customers_response.json()
            if customers_response.status_code == 200
            else []
        )

        ai_conversations = (
            ai_response.json()
            if ai_response.status_code == 200
            else []
        )

        businesses = (
            business_response.json()
            if business_response.status_code == 200
            else []
        )

        automation_rows = (
            automation_response.json()
            if automation_response.status_code == 200
            else []
        )

        automation = (
            automation_rows[0]
            if automation_rows
            else {
                "ai_replies":
                    True,

                "message_automation":
                    True,

                "task_automation":
                    True
            }
        )

        return jsonify({

            "success":
                True,

            "report": {

                "business":
                    businesses[0]
                    if businesses
                    else None,

                "total_customers":
                    len(customers),

                "total_ai_conversations":
                    len(ai_conversations),

                "total_ai_replies":
                    len([
                        x
                        for x in ai_conversations
                        if str(
                            x.get(
                                "answer",
                                ""
                            )
                        ).strip()
                    ]),

                "automation":
                    automation,

                "customers":
                    customers,

                "ai_conversations":
                    ai_conversations
            }
        })

    except Exception as error:

        print(
            "Reports exception:",
            error
        )

        traceback.print_exc()

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
