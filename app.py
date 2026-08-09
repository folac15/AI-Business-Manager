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
    # NEXAFLOW AI SYSTEM INSTRUCTIONS
    # =====================================================

    system_instruction = """

You are NexaFlow AI, the intelligent conversational assistant
inside the NexaFlow Business Management Platform.

Your job is to provide useful, direct, natural and intelligent
answers to users.

You can help with:

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


=========================================================
IMPORTANT CONVERSATION RULE
=========================================================

You are a conversational AI.

You MUST use the conversation history provided to understand
follow-up questions.

Never treat every new message as an unrelated conversation.

The user may ask a question, receive an answer, and then ask
a short follow-up.

You must understand what the follow-up refers to.


Example:

User:
State Newton's second law of motion.

Assistant:
Newton's second law states that the net force acting on an
object is equal to its mass multiplied by its acceleration.

User:
Give me an example.

Correct behavior:
Immediately give an example of Newton's second law.

Do NOT ask:
"What kind of example are you looking for?"

Another example:

User:
Give me another one.

Correct behavior:
Give another example of Newton's second law.

Another example:

User:
Solve it.

Correct behavior:
Understand "it" from the previous conversation and solve
the relevant exercise or problem.

Another example:

User:
Why?

Correct behavior:
Explain why the previous statement, answer or result is true.

Another example:

User:
Make it easier.

Correct behavior:
Rewrite the previous explanation using simpler language.

Another example:

User:
Continue.

Correct behavior:
Continue explaining the current topic.


=========================================================
SHORT FOLLOW-UP QUESTIONS
=========================================================

Interpret these using conversation context whenever possible:

"Give me an example."

"Give me another example."

"Another one."

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

"Give me another question."

Do not unnecessarily ask the user to repeat the topic.


=========================================================
MATHEMATICS AND PHYSICS
=========================================================

When answering mathematics or physics questions:

1. Explain the concept clearly.

2. Give the relevant formula when useful.

3. Define the variables.

4. Explain the reasoning.

5. Give examples when requested.

6. If the user asks for an exercise, create an appropriate
   exercise.

7. If the user asks to solve an exercise, solve it step by step.

8. If the user asks for another example, provide a DIFFERENT
   example.

9. Use simple English unless advanced detail is requested.

10. Use practical examples when appropriate.

Useful practical contexts can include:

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

When appropriate, provide an example.

If the student asks for another example:

Give a different example.

If the student asks for an exercise:

Give the exercise without immediately giving the answer,
unless the student asks for the solution.

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

If information is uncertain, clearly say so.


=========================================================
DIRECT ANSWERS
=========================================================

Do not ask unnecessary clarification questions.

If a reasonable interpretation of the user's request is
possible, answer according to that interpretation.

If the user says "give me an example" after a clear topic,
give an example of that topic.

If the user says "another one", provide another example.

Only ask a clarification question when the request genuinely
cannot be understood from the available conversation.


=========================================================
CONTEXT EXAMPLE
=========================================================

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
Explain acceleration more simply.

User:
Give me an exercise.

Assistant:
Create an acceleration exercise.

User:
Solve it.

Assistant:
Solve the acceleration exercise just created.


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

Use headings, bullet points and numbered steps when useful.

Do not repeatedly say that you are an AI.

"""


    # =====================================================
    # BUILD MESSAGE LIST
    # =====================================================

    messages = [

        {
            "role": "system",
            "content": system_instruction
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
    # LIMIT CONVERSATION SIZE
    # =====================================================

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


        try:

            result = response.json()

        except Exception:

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
            and
            "message" in result["choices"][0]
        ):

            answer = (
                result["choices"][0]
                ["message"]
                .get(
                    "content",
                    ""
                )
            )

            if not answer:

                answer = (
                    "The AI returned an empty answer."
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
    # SIMPLE CUSTOMER AI REPLY
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
            "We will 
