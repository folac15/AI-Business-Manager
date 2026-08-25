from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
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

WHATSAPP_VERIFY_TOKEN = os.environ.get(
    "WHATSAPP_VERIFY_TOKEN"
)

WHATSAPP_ACCESS_TOKEN = os.environ.get(
    "WHATSAPP_ACCESS_TOKEN"
)

WHATSAPP_PHONE_NUMBER_ID = os.environ.get(
    "WHATSAPP_PHONE_NUMBER_ID"
)

WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get(
    "WHATSAPP_BUSINESS_ACCOUNT_ID"
)


# =========================================================
# SUPABASE TABLE URLS
# =========================================================

CUSTOMERS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/customers"
)

BUSINESS_ACCOUNTS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/business_accounts"
)

AUTOMATION_SETTINGS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/automation_settings"
)

AI_CONVERSATIONS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/ai_conversations"
)

INTEGRATIONS_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/integrations"
)

MESSAGES_URL = (
    SUPABASE_PROJECT_URL + "/rest/v1/messages"
)


# =========================================================
# TIME
# =========================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# SUPABASE ADMIN HEADERS
# =========================================================

def supabase_headers(prefer=None):

    headers = {
        "apikey": str(SUPABASE_SECRET_KEY or ""),
        "Authorization": (
            "Bearer "
            + str(SUPABASE_SECRET_KEY or "")
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
# API STATUS
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

    if not SUPABASE_SECRET_KEY:

        print(
            "SUPABASE_SECRET_KEY is not configured."
        )

        return None

    try:

        response = requests.get(

            SUPABASE_PROJECT_URL
            + "/auth/v1/user",

            headers={
                "apikey":
                    SUPABASE_SECRET_KEY,

                "Authorization":
                    "Bearer "
                    + access_token
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
# AI CONVERSATION SAVE
# =========================================================

def save_ai_conversation(
    user_id,
    question,
    answer
):

    if not user_id:

        print(
            "AI conversation not saved: "
            "no authenticated user."
        )

        return False

    conversation_data = {

        "user_id":
            user_id,

        "question":
            question,

        "answer":
            answer,

        "created_at":
            now_iso()
    }

    try:

        response = requests.post(

            AI_CONVERSATIONS_URL,

            headers=supabase_headers(
                "return=representation"
            ),

            json=conversation_data,

            timeout=15
        )

        print(
            "AI conversation SAVE status:",
            response.status_code
        )

        print(
            "AI conversation SAVE response:",
            response.text
        )

        if response.status_code not in (
            200,
            201
        ):

            return False

        return True

    except Exception as error:

        print(
            "AI conversation SAVE exception:",
            error
        )

        return False


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

    user = get_authenticated_user()

    user_id = None

    if user:
        user_id = user.get("id")

    messages = [
        {
            "role": "system",
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

            role = item.get("role")
            content = item.get("content")

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
                "role": role,
                "content": content
            })

    messages.append({
        "role": "user",
        "content": question
    })

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
                    "application/json",

                "HTTP-Referer":
                    SUPABASE_PROJECT_URL,

                "X-Title":
                    "NexaFlow AI"
            },

            json={

                "model":
                    "openai/gpt-oss-20b:free",

                "messages":
                    messages
            },

            timeout=60
        )

        print(
            "OpenRouter status:",
            response.status_code
        )

        try:

            result = response.json()

        except ValueError:

            result = {}

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

        answer = ""

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

        if not answer:

            answer = (
                "The AI did not return an answer."
            )

        saved = save_ai_conversation(
            user_id,
            question,
            answer
        )

        print(
            "AI conversation saved:",
            saved
        )

        return jsonify({

            "success":
                True,

            "answer":
                answer,

            "conversation_saved":
                saved

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

    user_id = user["id"]

    try:

        response = requests.get(

            CUSTOMERS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "order":
                    "created_at.desc"

            },

            timeout=15
        )

        print(
            "Customers GET status:",
            response.status_code
        )

        print(
            "Customers GET response:",
            response.text
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

    user_id = user["id"]

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

    phone = str(
        data.get(
            "phone",
            data.get(
                "phone_number",
                ""
            )
        )
    ).strip()

    email = str(
        data.get(
            "email",
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
            data.get(
                "customer_message",
                ""
            )
        )
    ).strip()

    ai_reply = str(
        data.get(
            "ai_reply",
            ""
        )
    ).strip()

    if not name:

        return jsonify({

            "error":
                "Customer name is required."

        }), 400

    customer_data = {

        "user_id":
            user_id,

        "name":
            name,

        "phone":
            phone,

        "email":
            email,

        "location":
            location,

        "message":
            message,

        "ai_reply":
            ai_reply,

        "created_at":
            now_iso()
    }

    try:

        response = requests.post(

            CUSTOMERS_URL,

            headers=supabase_headers(
                "return=representation"
            ),

            json=customer_data,

            timeout=15
        )

        print(
            "Customer SAVE status:",
            response.status_code
        )

        print(
            "Customer SAVE response:",
            response.text
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

        try:

            result = response.json()

        except ValueError:

            result = []

        saved_customer = (

            result[0]

            if (
                isinstance(
                    result,
                    list
                )
                and result
            )

            else customer_data
        )

        return jsonify({

            "success":
                True,

            "customer":
                saved_customer,

            "message":
                "Customer saved successfully."

        })

    except Exception as error:

        print(
            "Customer SAVE exception:",
            error
        )

        return jsonify({

            "success":
                False,

            "error":
                "Unable to save customer: "
                + str(error)

        }), 500


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

        response = requests.delete(

            CUSTOMERS_URL,

            headers=supabase_headers(),

            params={

                "id":
                    "eq." + str(
                        customer_id
                    ),

                "user_id":
                    "eq." + user["id"]

            },

            timeout=15
        )

        print(
            "Customer DELETE status:",
            response.status_code
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

        return jsonify({

            "error":
                str(error)

        }), 500


# =========================================================
# DASHBOARD STATISTICS
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

        customers_response = requests.get(

            CUSTOMERS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "id",

                "user_id":
                    "eq." + user_id
            },

            timeout=15
        )

        if customers_response.status_code == 200:

            customers = (
                customers_response.json()
            )

        else:

            print(
                "Dashboard customer error:",
                customers_response.text
            )

            customers = []

        conversations_response = requests.get(

            AI_CONVERSATIONS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "id",

                "user_id":
                    "eq." + user_id
            },

            timeout=15
        )

        if conversations_response.status_code == 200:

            conversations = (
                conversations_response.json()
            )

        else:

            print(
                "Dashboard AI error:",
                conversations_response.text
            )

            conversations = []

        business_response = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "id",

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"
            },

            timeout=15
        )

        if business_response.status_code == 200:

            businesses = (
                business_response.json()
            )

        else:

            businesses = []

        # -------------------------------------------------
        # WHATSAPP STATISTICS
        # -------------------------------------------------

        whatsapp_messages = []

        whatsapp_response = requests.get(

            MESSAGES_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "id,direction,status",

                "user_id":
                    "eq." + user_id,

                "platform":
                    "eq.whatsapp"

            },

            timeout=15
        )

        if whatsapp_response.status_code == 200:

            whatsapp_messages = (
                whatsapp_response.json()
            )

        else:

            print(
                "Dashboard WhatsApp error:",
                whatsapp_response.text
            )

        whatsapp_incoming = len([

            item

            for item in whatsapp_messages

            if item.get("direction")
            == "inbound"

        ])

        whatsapp_outgoing = len([

            item

            for item in whatsapp_messages

            if item.get("direction")
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
                    whatsapp_incoming,

                "whatsapp_outgoing":
                    whatsapp_outgoing,

                "reports":
                    len(customers)
                    + len(conversations),

                "business_account":
                    1
                    if businesses
                    else 0
            }

        })

    except Exception as error:

        print(
            "Dashboard statistics exception:",
            error
        )

        return jsonify({

            "error":
                str(error)

        }), 500


# =========================================================
# AI CONVERSATION HISTORY
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

        response = requests.get(

            AI_CONVERSATIONS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user["id"],

                "order":
                    "created_at.desc"
            },

            timeout=15
        )

        print(
            "AI conversation HISTORY status:",
            response.status_code
        )

        if response.status_code != 200:

            return jsonify({

                "error":
                    "Unable to load AI conversations: "
                    + response.text

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
            "AI conversation history exception:",
            error
        )

        return jsonify({

            "error":
                str(error)

        }), 500


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

        customer_response = requests.get(

            CUSTOMERS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "order":
                    "created_at.desc"
            },

            timeout=15
        )

        if customer_response.status_code != 200:

            return jsonify({

                "error":
                    "Unable to load customer report: "
                    + customer_response.text

            }), customer_response.status_code

        customers = customer_response.json()

        ai_response = requests.get(

            AI_CONVERSATIONS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "order":
                    "created_at.desc"
            },

            timeout=15
        )

        if ai_response.status_code == 200:

            ai_conversations = (
                ai_response.json()
            )

        else:

            print(
                "Reports AI error:",
                ai_response.text
            )

            ai_conversations = []

        business_response = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=supabase_headers(),

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

        if business_response.status_code == 200:

            businesses = (
                business_response.json()
            )

        else:

            businesses = []

        automation_response = requests.get(

            AUTOMATION_SETTINGS_URL,

            headers=supabase_headers(),

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

        if automation_response.status_code == 200:

            automation_rows = (
                automation_response.json()
            )

        else:

            automation_rows = []

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

        total_customers = len(
            customers
        )

        total_conversations = len(
            ai_conversations
        )

        total_ai_replies = len([

            item

            for item in ai_conversations

            if str(
                item.get(
                    "answer",
                    ""
                )
            ).strip()
        ])

        return jsonify({

            "success":
                True,

            "report": {

                "business":
                    (
                        businesses[0]
                        if businesses
                        else None
                    ),

                "total_customers":
                    total_customers,

                "total_ai_conversations":
                    total_conversations,

                "total_ai_replies":
                    total_ai_replies,

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
            "Reports GET exception:",
            error
        )

        return jsonify({

            "error":
                "Unable to load reports: "
                + str(error)

        }), 500


# =========================================================
# AUTOMATION SETTINGS - GET
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

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user["id"],

                "limit":
                    "1"
            },

            timeout=15
        )

        if response.status_code != 200:

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

        return jsonify({

            "error":
                str(error)

        }), 500


# =========================================================
# AUTOMATION SETTINGS - SAVE
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

    automation = {

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

        response = requests.post(

            AUTOMATION_SETTINGS_URL,

            headers=supabase_headers(
                "resolution=merge-duplicates,"
                "return=representation"
            ),

            json=automation,

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

        try:

            result = response.json()

        except ValueError:

            result = []

        saved = (

            result[0]

            if (
                isinstance(
                    result,
                    list
                )
                and result
            )

            else automation
        )

        return jsonify({

            "success":
                True,

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
# AUTOMATION TOGGLE
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

    value = data.get("value")

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
            now_iso()
    }

    try:

        check = requests.get(

            AUTOMATION_SETTINGS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "id",

                "user_id":
                    "eq." + user["id"],

                "limit":
                    "1"
            },

            timeout=15
        )

        if check.status_code != 200:

            return jsonify({

                "error":
                    check.text

            }), check.status_code

        existing = check.json()

        if existing:

            response = requests.patch(

                AUTOMATION_SETTINGS_URL,

                headers=supabase_headers(
                    "return=representation"
                ),

                params={

                    "user_id":
                        "eq." + user["id"]
                },

                json=update_data,

                timeout=15
            )

        else:

            new_settings = {

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

            new_settings[setting] = value

            response = requests.post(

                AUTOMATION_SETTINGS_URL,

                headers=supabase_headers(
                    "return=representation"
                ),

                json=new_settings,

                timeout=15
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

        try:

            result = response.json()

        except ValueError:

            result = []

        return jsonify({

            "success":
                True,

            "message":
                "Automation setting updated successfully.",

            "setting":
                setting,

            "value":
                value,

            "automation": (

                result[0]

                if (
                    isinstance(
                        result,
                        list
                    )
                    and result
                )

                else None
            )
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
# BUSINESS ACCOUNT - GET / SAVE
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

            response = requests.get(

                BUSINESS_ACCOUNTS_URL,

                headers=supabase_headers(),

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

                return jsonify({

                    "error":
                        response.text

                }), response.status_code

            businesses = response.json()

            return jsonify({

                "business":
                    (
                        businesses[0]
                        if businesses
                        else None
                    )
            })

        except Exception as error:

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

        check = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "id",

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"
            },

            timeout=15
        )

        if check.status_code != 200:

            return jsonify({

                "error":
                    check.text

            }), check.status_code

        existing = check.json()

        if existing:

            business_id = existing[0]["id"]

            response = requests.patch(

                BUSINESS_ACCOUNTS_URL,

                headers=supabase_headers(
                    "return=representation"
                ),

                params={

                    "id":
                        "eq." + str(
                            business_id
                        ),

                    "user_id":
                        "eq." + user_id
                },

                json=business_data,

                timeout=15
            )

        else:

            response = requests.post(

                BUSINESS_ACCOUNTS_URL,

                headers=supabase_headers(
                    "return=representation"
                ),

                json=business_data,

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

        try:

            saved = response.json()

        except ValueError:

            saved = []

        return jsonify({

            "success":
                True,

            "business": (

                saved[0]

                if (
                    isinstance(
                        saved,
                        list
                    )
                    and saved
                )

                else business_data
            ),

            "message":
                "Business settings saved successfully."
        })

    except Exception as error:

        return jsonify({

            "error":
                str(error)

        }), 500


# =========================================================
# BUSINESS LOGO UPLOAD
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

    if (
        not logo_file
        or not logo_file.filename
    ):

        return jsonify({

            "error":
                "No logo file was selected."

        }), 400

    try:

        file_bytes = logo_file.read()

        if not file_bytes:

            return jsonify({

                "error":
                    "The selected logo file is empty."

            }), 400

        filename = logo_file.filename

        allowed_extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp"
        )

        if not filename.lower().endswith(
            allowed_extensions
        ):

            return jsonify({

                "error":
                    "Unsupported logo format."

            }), 400

        bucket_name = "business-logos"

        user_id = user["id"]

        extension = os.path.splitext(
            filename
        )[1].lower()

        storage_path = (
            user_id
            + "/business-logo"
            + extension
        )

        storage_url = (
            SUPABASE_PROJECT_URL
            + "/storage/v1/object/"
            + bucket_name
            + "/"
            + storage_path
        )

        upload_headers = {

            "Authorization":
                "Bearer "
                + str(
                    SUPABASE_SECRET_KEY
                ),

            "apikey":
                SUPABASE_SECRET_KEY,

            "Content-Type":
                logo_file.content_type
                or "application/octet-stream",

            "x-upsert":
                "true"
        }

        upload_response = requests.post(

            storage_url,

            headers=upload_headers,

            data=file_bytes,

            timeout=30
        )

        print(
            "Logo upload status:",
            upload_response.status_code
        )

        if upload_response.status_code not in (
            200,
            201
        ):

            return jsonify({

                "error":
                    "Logo upload failed: "
                    + upload_response.text

            }), upload_response.status_code

        logo_url = (
            SUPABASE_PROJECT_URL
            + "/storage/v1/object/public/"
            + bucket_name
            + "/"
            + storage_path
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
            "Logo upload exception:",
            error
        )

        return jsonify({

            "error":
                "Logo upload error: "
                + str(error)

        }), 500


# =========================================================
# WHATSAPP - GET INTEGRATIONS
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

        response = requests.get(

            INTEGRATIONS_URL,

            headers=supabase_headers(),

            params={
                "select": "*",
                "user_id":
                    "eq." + user["id"],
                "order":
                    "created_at.desc"
            },

            timeout=15
        )

        if response.status_code != 200:

            return jsonify({
                "error":
                    response.text
            }), response.status_code

        integrations = response.json()

        return jsonify({

            "success": True,

            "integrations":
                integrations,

            "count":
                len(integrations)

        })

    except Exception as error:

        print(
            "Integrations GET exception:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


# =========================================================
# WHATSAPP - CREATE / UPDATE INTEGRATION
# =========================================================

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
            WHATSAPP_BUSINESS_ACCOUNT_ID or ""
        )
    ).strip()

    access_token = str(
        data.get(
            "access_token",
            WHATSAPP_ACCESS_TOKEN or ""
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
            WHATSAPP_PHONE_NUMBER_ID or ""
        )
    ).strip()

    if not phone_number_id:

        return jsonify({
            "error":
                "WhatsApp phone number ID is required."
        }), 400

    integration_data = {

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

        check = requests.get(

            INTEGRATIONS_URL,

            headers=supabase_headers(),

            params={

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

            },

            timeout=15
        )

        if check.status_code != 200:

            return jsonify({
                "error":
                    check.text
            }), check.status_code

        existing = check.json()

        if existing:

            integration_id = existing[0]["id"]

            response = requests.patch(

                INTEGRATIONS_URL,

                headers=supabase_headers(
                    "return=representation"
                ),

                params={

                    "id":
                        "eq."
                        + str(integration_id),

                    "user_id":
                        "eq."
                        + user["id"]

                },

                json=integration_data,

                timeout=15
            )

        else:

            response = requests.post(

                INTEGRATIONS_URL,

                headers=supabase_headers(
                    "return=representation"
                ),

                json=integration_data,

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

        try:

            result = response.json()

        except ValueError:

            result = []

        saved = (

            result[0]

            if (
                isinstance(
                    result,
                    list
                )
                and result
            )

            else integration_data
        )

        return jsonify({

            "success":
                True,

            "integration":
                saved,

            "message":
                "WhatsApp integration saved successfully."

        })

    except Exception as error:

        print(
            "Integration SAVE exception:",
            error
        )

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# WHATSAPP - DELETE INTEGRATION
# =========================================================

@app.route(
    "/api/integrations/<int:integration_id>",
    methods=["DELETE"]
)
def delete_integration(
    integration_id
):

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    try:

        response = requests.delete(

            INTEGRATIONS_URL,

            headers=supabase_headers(),

            params={

                "id":
                    "eq."
                    + str(integration_id),

                "user_id":
                    "eq."
                    + user["id"]

            },

            timeout=15
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

        return jsonify({
            "error":
                str(error)
        }), 500


# =========================================================
# WHATSAPP - FIND BUSINESS FROM PHONE NUMBER ID
# =========================================================

def find_whatsapp_integration(
    phone_number_id
):

    app.logger.warning(
        "========== WHATSAPP INTEGRATION LOOKUP =========="
    )

    app.logger.warning(
        "Incoming phone_number_id: %s",
        phone_number_id
    )

    if not phone_number_id:

        app.logger.warning(
            "No phone_number_id received."
        )

        return None

    try:

        response = requests.get(

            INTEGRATIONS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "platform":
                    "eq.whatsapp"

            },

            timeout=15
        )

        app.logger.warning(
            "Integration lookup HTTP status: %s",
            response.status_code
        )

        app.logger.warning(
            "Integration lookup response: %s",
            response.text
        )

        if response.status_code != 200:

            return None

        integrations = response.json()

        app.logger.warning(
            "Number of WhatsApp integrations found: %s",
            len(integrations)
            if isinstance(integrations, list)
            else 0
        )

        for integration in integrations:

            settings = (
                integration.get("settings")
                or {}
            )

            stored_phone_number_id = str(
                settings.get(
                    "phone_number_id",
                    ""
                )
            ).strip()

            app.logger.warning(
                "Checking stored phone_number_id: %s",
                stored_phone_number_id
            )

            if (
                stored_phone_number_id
                == str(phone_number_id).strip()
            ):

                app.logger.warning(
                    "========== MATCH FOUND =========="
                )

                app.logger.warning(
                    "Integration ID: %s",
                    integration.get("id")
                )

                app.logger.warning(
                    "User ID: %s",
                    integration.get("user_id")
                )

                return integration

        app.logger.warning(
            "========== NO MATCH FOUND =========="
        )

        return None

    except Exception as error:

        app.logger.exception(
            "WhatsApp integration lookup exception: %s",
            error
        )

        return None


# =========================================================
# WHATSAPP - FIND OR CREATE CUSTOMER
# =========================================================

def find_or_create_whatsapp_customer(
    user_id,
    phone,
    name=""
):

    if not phone:

        return None

    try:

        response = requests.get(

            CUSTOMERS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user_id,

                "phone":
                    "eq." + phone,

                "limit":
                    "1"

            },

            timeout=15
        )

        if response.status_code != 200:

            print(
                "WhatsApp customer lookup error:",
                response.text
            )

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

        create_response = requests.post(

            CUSTOMERS_URL,

            headers=supabase_headers(
                "return=representation"
            ),

            json=customer_data,

            timeout=15
        )

        if create_response.status_code not in (
            200,
            201
        ):

            print(
                "WhatsApp customer creation error:",
                create_response.text
            )

            return None

        created = create_response.json()

        if created:

            return created[0]

        return customer_data

    except Exception as error:

        print(
            "WhatsApp customer exception:",
            error
        )

        return None


# =========================================================
# WHATSAPP - CHECK DUPLICATE MESSAGE
# =========================================================

def whatsapp_message_exists(
    external_message_id
):

    if not external_message_id:

        return False

    try:

        response = requests.get(

            MESSAGES_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "id",

                "external_message_id":
                    "eq."
                    + external_message_id,

                "limit":
                    "1"

            },

            timeout=15
        )

        if response.status_code != 200:

            return False

        messages = response.json()

        return bool(messages)

    except Exception:

        return False


# =========================================================
# WHATSAPP - STORE INCOMING MESSAGE
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

    user_id = integration["user_id"]

    customer = find_or_create_whatsapp_customer(
        user_id,
        sender_phone,
        sender_name
    )

    customer_id = None

    if customer:

        customer_id = customer.get("id")

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
            external_message_id or "",

        "direction":
            "inbound",

        "sender_name":
            sender_name or "",

        "sender_phone":
            sender_phone or "",

        "message":
            message_text or "",

        "ai_generated":
            False,

        "ai_reply":
            "",

        "status":
            "received",

        "metadata":
            {
                "source":
                    "whatsapp_webhook"
            },

        "created_at":
            now_iso(),

        "updated_at":
            now_iso()

    }

    try:

        response = requests.post(

            MESSAGES_URL,

            headers=supabase_headers(
                "return=representation"
            ),

            json=message_data,

            timeout=15
        )

        print(
            "WhatsApp message SAVE status:",
            response.status_code
        )

        print(
            "WhatsApp message SAVE response:",
            response.text
        )

        if response.status_code not in (
            200,
            201
        ):

            return None

        result = response.json()

        if result:

            return result[0]

        return message_data

    except Exception as error:

        print(
            "WhatsApp message SAVE exception:",
            error
        )

        return None


# =========================================================
# WHATSAPP - GET MESSAGES
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

    user_id = user["id"]

    customer_id = request.args.get(
        "customer_id",
        ""
    ).strip()

    limit = request.args.get(
        "limit",
        "100"
    ).strip()

    try:

        limit_number = int(limit)

    except ValueError:

        limit_number = 100

    limit_number = max(
        1,
        min(
            limit_number,
            500
        )
    )

    params = {

        "select":
            "*",

        "user_id":
            "eq." + user_id,

        "platform":
            "eq.whatsapp",

        "order":
            "created_at.desc",

        "limit":
            str(limit_number)

    }

    if customer_id:

        params["customer_id"] = (
            "eq." + customer_id
        )

    try:

        response = requests.get(

            MESSAGES_URL,

            headers=supabase_headers(),

            params=params,

            timeout=15
        )

        print(
            "WhatsApp messages GET status:",
            response.status_code
        )

        print(
            "WhatsApp messages GET response:",
            response.text
        )

        if response.status_code != 200:

            return jsonify({

                "success":
                    False,

                "error":
                    "Unable to load WhatsApp messages: "
                    + response.text

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
            "WhatsApp messages GET exception:",
            error
        )

        return jsonify({

            "success":
                False,

            "error":
                "Unable to load WhatsApp messages: "
                + str(error)

        }), 500


# =========================================================
# WHATSAPP - GET SINGLE MESSAGE
# =========================================================

@app.route(
    "/api/messages/<int:message_id>",
    methods=["GET"]
)
def get_single_message(message_id):

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
                "Invalid or expired login session."
        }), 401

    try:

        response = requests.get(

            MESSAGES_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "*",

                "id":
                    "eq." + str(
                        message_id
                    ),

                "user_id":
                    "eq." + user["id"],

                "platform":
                    "eq.whatsapp",

                "limit":
                    "1"

            },

            timeout=15
        )

        if response.status_code != 200:

            return jsonify({

                "error":
                    response.text

            }), response.status_code

        messages = response.json()

        if not messages:

            return jsonify({

                "error":
                    "WhatsApp message not found."

            }), 404

        return jsonify({

            "success":
                True,

            "message":
                messages[0]

        })

    except Exception as error:

        print(
            "Single WhatsApp message exception:",
            error
        )

        return jsonify({

            "error":
                str(error)

        }), 500


# =========================================================
# WHATSAPP - GET CUSTOMER CONVERSATION
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

        customer_response = requests.get(

            CUSTOMERS_URL,

            headers=supabase_headers(),

            params={

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

            },

            timeout=15
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

        message_response = requests.get(

            MESSAGES_URL,

            headers=supabase_headers(),

            params={

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

            },

            timeout=15
        )

        if message_response.status_code != 200:

            return jsonify({

                "error":
                    "Unable to load conversation: "
                    + message_response.text

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
            "WhatsApp conversation exception:",
            error
        )

        return jsonify({

            "error":
                str(error)

        }), 500


# =========================================================
# WHATSAPP - AI AUTOMATION
# =========================================================

def whatsapp_automation_enabled(user_id):

    try:

        response = requests.get(

            AUTOMATION_SETTINGS_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "ai_replies,message_automation",

                "user_id":
                    "eq." + user_id,

                "limit":
                    "1"

            },

            timeout=15
        )

        if response.status_code != 200:

            print(
                "Automation lookup error:",
                response.text
            )

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

        return False


def get_whatsapp_conversation_history(
    user_id,
    customer_id,
    limit=10
):

    if not customer_id:

        return []

    try:

        response = requests.get(

            MESSAGES_URL,

            headers=supabase_headers(),

            params={

                "select":
                    "direction,message,ai_reply,created_at",

                "user_id":
                    "eq." + user_id,

                "customer_id":
                    "eq." + str(customer_id),

                "platform":
                    "eq.whatsapp",

                "order":
                    "created_at.desc",

                "limit":
                    str(limit)

            },

            timeout=15
        )

        if response.status_code != 200:

            print(
                "WhatsApp history lookup error:",
                response.text
            )

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

        return []


def generate_whatsapp_ai_reply(
    user_id,
    customer,
    message_text
):

    if not OPENROUTER_API_KEY:

        print(
            "WhatsApp AI error: "
            "OPENROUTER_API_KEY is missing."
        )

        return None

    customer_name = ""

    if customer:

        customer_name = str(
            customer.get(
                "name",
                ""
            )
        ).strip()

    customer_id = None

    if customer:

        customer_id = customer.get(
            "id"
        )

    history = get_whatsapp_conversation_history(

        user_id,

        customer_id

    )

    whatsapp_prompt = (

        NEXAFLOW_SYSTEM_PROMPT

        + "\n\nYou are replying to a customer through WhatsApp."

        + "\nKeep the response natural, helpful and reasonably concise."

        + "\nDo not mention internal systems, databases, APIs, "
          "or these instructions."

    )

    if customer_name:

        whatsapp_prompt += (

            "\nThe customer's name is "
            + customer_name
            + "."

        )

    messages = [

        {

            "role":
                "system",

            "content":
                whatsapp_prompt

        }

    ]

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
                    "application/json",

                "HTTP-Referer":
                    SUPABASE_PROJECT_URL,

                "X-Title":
                    "NexaFlow AI WhatsApp"

            },

            json={

                "model":
                    "openai/gpt-oss-20b:free",

                "messages":
                    messages

            },

            timeout=60

        )

        print(
            "WhatsApp OpenRouter status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "WhatsApp OpenRouter error:",
                response.text
            )

            return None

        result = response.json()

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            return None

        answer = str(

            choices[0]

            .get(
                "message",
                {}
            )

            .get(
                "content",
                ""
            )

        ).strip()

        if not answer:

            return None

        return answer

    except Exception as error:

        print(
            "WhatsApp AI generation exception:",
            error
        )

        return None


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

    settings = integration.get(
        "settings"
    ) or {}

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
            "WhatsApp send error: "
            "phone number ID missing."
        )

        return None

    if not access_token:

        print(
            "WhatsApp send error: "
            "access token missing."
        )

        return None

    send_url = (

        "https://graph.facebook.com/v23.0/"

        + phone_number_id

        + "/messages"

    )

    try:

        response = requests.post(

            send_url,

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
            "WhatsApp SEND status:",
            response.status_code
        )

        print(
            "WhatsApp SEND response:",
            response.text
        )

        if response.status_code not in (
            200,
            201
        ):

            return None

        return response.json()

    except Exception as error:

        print(
            "WhatsApp SEND exception:",
            error
        )

        return None


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

        response = requests.post(

            MESSAGES_URL,

            headers=supabase_headers(
                "return=representation"
            ),

            json=message_data,

            timeout=15

        )

        print(
            "WhatsApp outgoing SAVE status:",
            response.status_code
        )

        if response.status_code not in (
            200,
            201
        ):

            print(
                "WhatsApp outgoing SAVE error:",
                response.text
            )

            return None

        result = response.json()

        if (
            isinstance(
                result,
                list
            )
            and result
        ):

            return result[0]

        return message_data

    except Exception as error:

        print(
            "WhatsApp outgoing SAVE exception:",
            error
        )

        return None


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

        response = requests.patch(

            MESSAGES_URL,

            headers=supabase_headers(
                "return=representation"
            ),

            params={

                "id":
                    "eq." + str(
                        message_id
                    )

            },

            json={

                "ai_reply":
                    ai_reply,

                "status":
                    "replied",

                "updated_at":
                    now_iso()

            },

            timeout=15

        )

        print(
            "Incoming WhatsApp update status:",
            response.status_code
        )

        if response.status_code not in (
            200,
            204
        ):

            print(
                "Incoming WhatsApp update error:",
                response.text
            )

            return False

        return True

    except Exception as error:

        print(
            "Incoming WhatsApp update exception:",
            error
        )

        return False


def process_whatsapp_ai_reply(
    integration,
    stored_message
):

    if (
        not integration
        or not stored_message
    ):

        return False

    user_id = integration.get(
        "user_id"
    )

    if not user_id:

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

        return False

    customer_id = stored_message.get(
        "customer_id"
    )

    customer = None

    if customer_id:

        try:

            response = requests.get(

                CUSTOMERS_URL,

                headers=supabase_headers(),

                params={

                    "select":
                        "*",

                    "id":
                        "eq."
                        + str(customer_id),

                    "user_id":
                        "eq." + user_id,

                    "limit":
                        "1"

                },

                timeout=15

            )

            if response.status_code == 200:

                rows = response.json()

                if rows:

                    customer = rows[0]

        except Exception as error:

            print(
                "WhatsApp customer retrieval exception:",
                error
            )

    ai_reply = generate_whatsapp_ai_reply(

        user_id,

        customer,

        message_text

    )

    if not ai_reply:

        print(
            "WhatsApp AI did not generate a reply."
        )

        return False

    whatsapp_response = send_whatsapp_message(

        integration,

        recipient_phone,

        ai_reply

    )

    if not whatsapp_response:

        return False

    outgoing = store_whatsapp_outgoing_message(

        integration,

        customer,

        recipient_phone,

        ai_reply,

        whatsapp_response

    )

    if not outgoing:

        return False

    update_incoming_message_with_ai_reply(

        stored_message.get("id"),

        ai_reply

    )

    return True


# =========================================================
# WHATSAPP - WEBHOOK VERIFICATION
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

        return challenge or "", 200

    return "Forbidden", 403


# =========================================================
# WHATSAPP - RECEIVE WEBHOOK
# =========================================================

@app.route(
    "/api/whatsapp/webhook",
    methods=["POST"]
)
def whatsapp_webhook():

    app.logger.warning(
        "========== WHATSAPP WEBHOOK START =========="
    )

    payload = request.get_json(
        silent=True
    ) or {}

    app.logger.warning(
        "========== WHATSAPP PAYLOAD RECEIVED =========="
    )

    app.logger.warning(
        "WhatsApp payload: %s",
        payload
    )

    if payload.get(
        "object"
    ) != "whatsapp_business_account":

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

            integration = find_whatsapp_integration(
                phone_number_id
            )

            if not integration:

                print(
                    "No NexaFlow integration found for WhatsApp phone number:",
                    phone_number_id
                )

                continue

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

                contact_name = profile.get(
                    "name",
                    ""
                )

            for whatsapp_message in messages:

                message_id = whatsapp_message.get(
                    "id"
                )

                if whatsapp_message_exists(
                    message_id
                ):

                    print(
                        "Duplicate WhatsApp message ignored:",
                        message_id
                    )

                    continue

                sender_phone = whatsapp_message.get(
                    "from",
                    ""
                )

                message_type = whatsapp_message.get(
                    "type",
                    ""
                )

                message_text = ""

                if message_type == "text":

                    message_text = whatsapp_message.get(
                        "text",
                        {}
                    ).get(
                        "body",
                        ""
                    )

                else:

                    message_text = (
                        "["
                        + message_type
                        + " message]"
                    )

                stored = store_whatsapp_message(
                    integration,
                    sender_phone,
                    contact_name,
                    message_text,
                    message_id
                )

                if stored:

                    processed += 1

                    ai_replied = process_whatsapp_ai_reply(
                        integration,
                        stored
                    )

                    print(
                        "WhatsApp AI automatic reply sent:",
                        ai_replied
                    )

    return jsonify({

        "success":
            True,

        "processed":
            processed

    }), 200


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
