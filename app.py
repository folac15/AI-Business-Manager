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

AI_CONVERSATIONS_URL = (
    SUPABASE_PROJECT_URL
    + "/rest/v1/ai_conversations"
)


# =========================================================
# SUPABASE HEADERS
# =========================================================

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SECRET_KEY,
    "Authorization": (
        "Bearer "
        + str(SUPABASE_SECRET_KEY)
    ),
    "Content-Type": "application/json"
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
# API STATUS
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

    if not SUPABASE_SECRET_KEY:
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
# SAVE AI CONVERSATION
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
            datetime.utcnow().isoformat()

    }

    try:

        response = requests.post(

            AI_CONVERSATIONS_URL,

            headers={

                **SUPABASE_HEADERS,

                "Prefer":
                    "return=representation"

            },

            json=conversation_data,

            timeout=15

        )

        print(
            "AI conversation save status:",
            response.status_code
        )

        if response.status_code not in (
            200,
            201
        ):

            print(
                "AI conversation save error:",
                response.text
            )

            return False

        return True

    except Exception as error:

        print(
            "AI conversation save exception:",
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

        save_ai_conversation(
            user_id,
            question,
            answer
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

        response = requests.get(

            CUSTOMERS_URL,

            headers=SUPABASE_HEADERS,

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
            "Customers GET status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "Customers GET error:",
                response.text
            )

            return jsonify({

                "error":
                    response.text

            }), response.status_code

        customers = response.json()

        return jsonify({

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
                str(error)

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
            ""
        )
    ).strip()

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    ai_reply = str(
        data.get(
            "ai_reply",
            ""
        )
    ).strip()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    email = str(
        data.get(
            "email",
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
            user["id"],

        "name":
            name,

        "message":
            message,

        "ai_reply":
            ai_reply,

        "phone":
            phone,

        "email":
            email,

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

            json=customer_data,

            timeout=15

        )

        print(
            "Customer SAVE status:",
            response.status_code
        )

        if response.status_code not in (
            200,
            201
        ):

            print(
                "Customer SAVE error:",
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

        saved_customer = (

            result[0]

            if (
                isinstance(result, list)
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

            "error":
                str(error)

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

            headers=SUPABASE_HEADERS,

            params={

                "id":
                    "eq." + str(customer_id),

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

        # -------------------------------------------------
        # CUSTOMERS
        # -------------------------------------------------

        customer_response = requests.get(

            CUSTOMERS_URL,

            headers=SUPABASE_HEADERS,

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user_id

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

        # -------------------------------------------------
        # AI CONVERSATIONS
        # -------------------------------------------------

        ai_response = requests.get(

            AI_CONVERSATIONS_URL,

            headers=SUPABASE_HEADERS,

            params={

                "select":
                    "*",

                "user_id":
                    "eq." + user_id

            },

            timeout=15

        )

        if ai_response.status_code != 200:

            print(
                "AI report load error:",
                ai_response.text
            )

            ai_conversations = []

        else:

            ai_conversations = (
                ai_response.json()
            )

        # -------------------------------------------------
        # BUSINESS
        # -------------------------------------------------

        business_response = requests.get(

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

        if business_response.status_code == 200:

            businesses = (
                business_response.json()
            )

        else:

            businesses = []

        # -------------------------------------------------
        # AUTOMATION
        # -------------------------------------------------

        automation_response = requests.get(

            AUTOMATION_SETTINGS_URL,

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

        # -------------------------------------------------
        # REPORT SUMMARY
        # -------------------------------------------------

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

        # -------------------------------------------------
        # CUSTOMERS
        # -------------------------------------------------

        customers_response = requests.get(

            CUSTOMERS_URL,

            headers=SUPABASE_HEADERS,

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

            customers = []

        # -------------------------------------------------
        # AI CONVERSATIONS
        # -------------------------------------------------

        conversations_response = requests.get(

            AI_CONVERSATIONS_URL,

            headers=SUPABASE_HEADERS,

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

            conversations = []

        # -------------------------------------------------
        # BUSINESS
        # -------------------------------------------------

        business_response = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=SUPABASE_HEADERS,

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

        return jsonify({

            "success":
                True,

            "stats": {

                "customers":
                    len(customers),

                "ai_conversations":
                    len(conversations),

                "business_account":
                    1
                    if businesses
                    else 0

            }

        })

    except Exception as error:

        print(
            "Dashboard statistics error:",
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

            headers=SUPABASE_HEADERS,

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
            "AI conversation history error:",
            error
        )

        return jsonify({

            "error":
                str(error)

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

            headers=SUPABASE_HEADERS,

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

        print(
            "Automation GET status:",
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
            datetime.utcnow().isoformat()

    }

    try:

        response = requests.post(

            AUTOMATION_SETTINGS_URL,

            headers={

                **SUPABASE_HEADERS,

                "Prefer":
                    "resolution=merge-duplicates,"
                    "return=representation"

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

            if (
                isinstance(result, list)
                and result
            )

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
            datetime.utcnow().isoformat()

    }

    try:

        check = requests.get(

            AUTOMATION_SETTINGS_URL,

            headers=SUPABASE_HEADERS,

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

            new_settings[setting] = value

            new_settings["updated_at"] = (
                datetime.utcnow().isoformat()
            )

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

            "automation": (

                result[0]

                if (
                    isinstance(result, list)
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

                return jsonify({

                    "error":
                        response.text

                }), response.status_code

            businesses = response.json()

            if businesses:

                return jsonify({

                    "business":
                        businesses[0]

                })

            return jsonify({

                "business":
                    None

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
            datetime.utcnow().isoformat()

    }

    try:

        check = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=SUPABASE_HEADERS,

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

                headers={

                    **SUPABASE_HEADERS,

                    "Prefer":
                        "return=representation"

                },

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

                headers={

                    **SUPABASE_HEADERS,

                    "Prefer":
                        "return=representation"

                },

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

        saved_business = (

            saved[0]

            if (
                isinstance(saved, list)
                and saved
            )

            else business_data

        )

        return jsonify({

            "success":
                True,

            "business":
                saved_business,

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
                    "Unsupported logo format. "
                    "Use JPG, JPEG, PNG, GIF or WEBP."

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
