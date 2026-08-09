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

OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY"
)

SUPABASE_SECRET_KEY = os.environ.get(
    "SUPABASE_SECRET_KEY"
)


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
    "apikey": SUPABASE_SECRET_KEY,
    "Authorization": "Bearer " + str(
        SUPABASE_SECRET_KEY
    ),
    "Content-Type": "application/json"
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
        or filename.endswith(".css")
        or filename.endswith(".js")
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
        "status": "online",
        "message": "NexaFlow AI API is working"
    })


# =========================================================
# HELPER — GET LOGGED-IN USER
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
# AI ASSISTANT API
# =========================================================

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

    conversation = data.get(
        "conversation",
        []
    )


    # =====================================================
    # CHECK QUESTION
    # =====================================================

    if question == "":

        return jsonify({

            "answer":
            "Please enter your question."

        }), 400


    # =====================================================
    # CHECK OPENROUTER KEY
    # =====================================================

    if not OPENROUTER_API_KEY:

        return jsonify({

            "answer":
            "OpenRouter API key is not configured."

        }), 500


    # =====================================================
    # NEXAFLOW AI INSTRUCTIONS
    # =====================================================

    system_instruction = """
You are NexaFlow AI, an intelligent conversational assistant
inside the NexaFlow Business Management Platform.

You help users with:

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
- Writing and communication
- Problem solving

=========================================================
CONVERSATION BEHAVIOR
=========================================================

You are a conversational AI, not a simple question-answer
machine.

Always use the conversation history provided to you.

Understand short follow-up questions from context.

For example:

User:
State Newton's second law of motion.

Assistant:
Newton's second law states that the net force acting on an
object is equal to its mass multiplied by its acceleration.

User:
Give me an example.

You should understand that "example" refers to Newton's second
law.

DO NOT ask:
"What kind of example are you looking for?"

Instead, immediately provide a suitable example.

Another example:

User:
Give me another one.

Understand that the user wants another example of the current
topic.

Another example:

User:
Solve it.

Understand that "it" refers to the most recent exercise or
problem.

Another example:

User:
Why?

Understand that the user is asking why the previous answer or
result is true.

Another example:

User:
Explain that more simply.

Rewrite the previous explanation in easier language.

=========================================================
FOLLOW-UP QUESTIONS
=========================================================

The following short messages should normally be interpreted
using the previous conversation:

"Give me an example."

"Another example."

"Give me another one."

"Explain."

"Explain that."

"Why?"

"How?"

"Continue."

"Go on."

"Solve it."

"Make it easier."

"Give me an exercise."

"Give me the answer."

"Give me the solution."

"Give me a Cameroon example."

"Give me a practical example."

Do not unnecessarily ask the user to repeat the subject.

=========================================================
MATHEMATICS AND PHYSICS
=========================================================

When explaining mathematics or physics:

1. Give the concept clearly.

2. Give the relevant formula when useful.

3. Define the variables.

4. Explain the reasoning.

5. Give a practical example when requested.

6. When the user asks for an exercise, create an appropriate
exercise.

7. When the user asks to solve an exercise, show the solution
step by step.

8. When appropriate, provide more than one example.

9. Use simple English unless the user asks for advanced detail.

10. Use practical Cameroon-related examples when appropriate.

For example, physics examples may involve:

- motorcycles
- cars
- trucks
- construction
- pumps
- water tanks
- electricity
- generators
- agricultural machines
- solar systems
- lifting equipment

Do not invent specific real-world facts.

=========================================================
EDUCATIONAL BEHAVIOR
=========================================================

When a student asks for an explanation:

Explain first.

Then give an example if appropriate.

If the student asks for another example:

Give a different example.

If the student asks for an exercise:

Give an exercise without immediately giving the answer unless
the student asks for the solution.

If the student asks for the solution:

Give a detailed step-by-step solution.

If the student makes a mistake:

Politely identify the mistake and explain how to correct it.

=========================================================
BUSINESS BEHAVIOR
=========================================================

For business questions:

Give practical recommendations.

Consider small and medium-sized businesses.

Consider African and Cameroonian business realities when
relevant.

Do not invent prices, statistics, regulations or market data.

When information is uncertain, clearly say so.

=========================================================
DIRECT ANSWERS
=========================================================

Do not ask unnecessary clarification questions.

If a reasonable interpretation of the user's request is
possible, answer according to that interpretation.

If there are several reasonable interpretations, give the most
useful interpretation first and briefly mention the alternative.

=========================================================
CONTEXT
=========================================================

Maintain the topic of the conversation.

For example:

User:
What is acceleration?

Assistant:
Acceleration is the rate at which velocity changes with time.

User:
Give me an example.

Assistant:
Give an example of acceleration.

User:
Make it easier.

Assistant:
Explain acceleration using simpler language.

User:
Give me an exercise.

Assistant:
Create an acceleration exercise.

User:
Solve it.

Assistant:
Solve the exercise you just created.

=========================================================
ACCURACY
=========================================================

Be accurate.

Do not fabricate information.

Do not claim to have performed an action that you did not
perform.

If you do not know something, say so.

=========================================================
STYLE
=========================================================

Be helpful, natural and conversational.

Do not make every answer unnecessarily long.

For simple questions, answer simply.

For complex questions, provide enough detail to make the answer
understandable.

Use headings, bullet points and numbered steps when they improve
clarity.
"""


    # =====================================================
    # BUILD MESSAGE LIST
    # =====================================================

    messages = [

        {
            "role":
            "system",

            "content":
            system_instruction
        }

    ]


    # =====================================================
    # ADD CONVERSATION HISTORY
    # =====================================================

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


            if role not in [
                "user",
                "assistant"
            ]:

                continue


            if not content:

                continue


            messages.append({

                "role":
                role,

                "content":
                str(content)

            })


    # =====================================================
    # ADD CURRENT QUESTION
    # =====================================================

    messages.append({

        "role":
        "user",

        "content":
        question

    })


    # =====================================================
    # LIMIT EXTREMELY LARGE CONVERSATIONS
    # =====================================================

    # Keep the system instruction plus the most recent
    # conversation messages.

    if len(messages) > 21:

        messages = (
            [messages[0]]
            +
            messages[-20:]
        )


    # =====================================================
    # SEND TO OPENROUTER
    # =====================================================

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

                "messages":
                messages

            },

            timeout=60

        )


        result = response.json()


        print(
            "OpenRouter status:",
            response.status_code
        )


        if response.status_code != 200:

            print(
                "OpenRouter error:",
                result
            )

            error_information = result.get(
                "error",
                result
            )

            return jsonify({

                "answer":
                "AI service error: " +
                str(
                    error_information
                )

            }), 500


        if (
            "choices" in result
            and
            len(result["choices"]) > 0
        ):

            answer = (
                result["choices"][0]
                ["message"]
                ["content"]
            )

        else:

            answer = (
                "The AI did not return an answer."
            )


    except Exception as error:

        print(
            "AI service exception:",
            error
        )

        return jsonify({

            "answer":
            "AI service connection error: " +
            str(error)

        }), 500


    # =====================================================
    # RETURN AI ANSWER
    # =====================================================

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

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
            "Invalid or expired login session."
        }), 401

    user_id = user["id"]

    try:

        response = requests.get(

            BUSINESS_ACCOUNTS_URL,

            headers=SUPABASE_HEADERS,

            params={

                "select": "*",

                "user_id":
                "eq." + user_id,

                "limit": "1"

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

        businesses = response.json()

        if not businesses:

            return jsonify({
                "business": None
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

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
            "Invalid or expired login session."
        }), 401

    data = request.get_json() or {}

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

    user = get_authenticated_user()

    if not user:

        return jsonify({
            "error":
            "Invalid or expired login session."
        }), 401

    # =====================================================
    # CURRENT USER UUID
    # =====================================================

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


    # =====================================================
    # SIMPLE AI CUSTOMER REPLY
    # =====================================================

    text = message.lower()

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


    # =====================================================
    # CUSTOMER RECORD
    # =====================================================

    customer = {

        "user_id":
        user_id,

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
                "retu
