from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import requests
import os
import json
import threading
import time
import traceback
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ================================================================
# NEXAFLOW AI BUSINESS MANAGEMENT PLATFORM
# ================================================================

PORT = int(os.environ.get("PORT", 5000))

print("=" * 60)
print("NexaFlow AI starting...")
print(f"Port: {PORT}")
print("WhatsApp AI background threading: ENABLED")
print("WhatsApp webhook handler: ROBUST MODE ENABLED")
print("=" * 60)

# ================================================================
# ENVIRONMENT VARIABLES
# ================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

WHATSAPP_ACCESS_TOKEN = os.environ.get(
    "WHATSAPP_ACCESS_TOKEN",
    os.environ.get("META_ACCESS_TOKEN", "")
).strip()

WHATSAPP_PHONE_NUMBER_ID = os.environ.get(
    "WHATSAPP_PHONE_NUMBER_ID",
    os.environ.get("META_PHONE_NUMBER_ID", "")
).strip()

WHATSAPP_VERIFY_TOKEN = os.environ.get(
    "WHATSAPP_VERIFY_TOKEN",
    os.environ.get("META_VERIFY_TOKEN", "")
).strip()

OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL",
    "openai/gpt-4o-mini"
).strip()

print("Environment diagnostics:")
print("SUPABASE_URL configured:", bool(SUPABASE_URL))
print("SUPABASE_KEY configured:", bool(SUPABASE_KEY))
print("OPENROUTER_API_KEY configured:", bool(OPENROUTER_API_KEY))
print("WHATSAPP_ACCESS_TOKEN configured:", bool(WHATSAPP_ACCESS_TOKEN))
print("WHATSAPP_PHONE_NUMBER_ID configured:", bool(WHATSAPP_PHONE_NUMBER_ID))
print("WHATSAPP_VERIFY_TOKEN configured:", bool(WHATSAPP_VERIFY_TOKEN))
print("OPENROUTER_MODEL:", OPENROUTER_MODEL)

# ================================================================
# IN-MEMORY FALLBACK STORAGE
# ================================================================

customers = []
messages = []

# Prevent duplicate WhatsApp webhook processing.
processed_whatsapp_message_ids = set()
processed_whatsapp_message_lock = threading.Lock()

# ================================================================
# GENERAL HELPERS
# ================================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def safe_json_response(data, status=200):
    return jsonify(data), status


def get_json_body():
    try:
        return request.get_json(silent=True) or {}
    except Exception:
        return {}


def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def supabase_available():
    return bool(SUPABASE_URL and SUPABASE_KEY)


def supabase_request(method, endpoint, **kwargs):
    if not supabase_available():
        return None

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{endpoint}"

    headers = kwargs.pop("headers", {})
    final_headers = supabase_headers()
    final_headers.update(headers)

    try:
        response = requests.request(
            method,
            url,
            headers=final_headers,
            timeout=30,
            **kwargs
        )

        print(
            f"SUPABASE {method} {endpoint}: "
            f"{response.status_code}"
        )

        if response.text:
            print("SUPABASE RESPONSE:", response.text[:2000])

        return response

    except Exception as exc:
        print("SUPABASE REQUEST ERROR:", repr(exc))
        traceback.print_exc()
        return None


# ================================================================
# BASIC ROUTES
# ================================================================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "status": "online",
        "service": "NexaFlow AI",
        "timestamp": now_iso(),
        "whatsapp": {
            "enabled": True,
            "phone_number_id_configured": bool(
                WHATSAPP_PHONE_NUMBER_ID
            ),
            "access_token_configured": bool(
                WHATSAPP_ACCESS_TOKEN
            )
        },
        "ai": {
            "enabled": bool(OPENROUTER_API_KEY),
            "model": OPENROUTER_MODEL
        },
        "supabase": {
            "configured": supabase_available()
        }
    })


# ================================================================
# AI SERVICE
# ================================================================

def generate_ai_response(question, conversation_context=None):
    """
    Generate an AI response through OpenRouter.

    This function deliberately returns a string instead of raising
    an exception so the WhatsApp worker can always finish cleanly.
    """

    question = (question or "").strip()

    if not question:
        return "Please send me a message and I will be happy to help."

    if not OPENROUTER_API_KEY:
        print("AI ERROR: OPENROUTER_API_KEY is not configured.")
        return (
            "Sorry, my AI service is not configured at the moment. "
            "Please try again later."
        )

    messages_payload = []

    # Keep existing conversational context when available.
    if conversation_context:
        for item in conversation_context:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if role in ("system", "user", "assistant") and content:
                messages_payload.append({
                    "role": role,
                    "content": str(content)
                })

    messages_payload.append({
        "role": "user",
        "content": question
    })

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages_payload,
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.environ.get(
            "APP_URL",
            "https://ai-business-manager.onrender.com"
        ),
        "X-Title": "NexaFlow AI Business Manager"
    }

    try:
        print("AI REQUEST START")
        print("AI MODEL:", OPENROUTER_MODEL)
        print("AI QUESTION:", question[:2000])

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )

        print("AI HTTP STATUS:", response.status_code)

        if response.text:
            print(
                "AI RAW RESPONSE:",
                response.text[:4000]
            )

        if response.status_code != 200:
            print(
                "AI REQUEST FAILED:",
                response.status_code,
                response.text[:2000]
            )

            return (
                "Sorry, I could not generate a response right now. "
                "Please try again."
            )

        data = response.json()

        choices = data.get("choices") or []

        if not choices:
            print("AI ERROR: No choices returned.")
            return (
                "Sorry, I could not generate a response right now."
            )

        message = choices[0].get("message") or {}
        answer = message.get("content")

        if isinstance(answer, list):
            parts = []

            for item in answer:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                elif item:
                    parts.append(str(item))

            answer = "".join(parts)

        answer = str(answer or "").strip()

        if not answer:
            print("AI ERROR: Empty AI answer.")
            return (
                "Sorry, I could not generate a response right now."
            )

        print("AI SUCCESS:", answer[:4000])

        return answer

    except requests.RequestException as exc:
        print("AI NETWORK ERROR:", repr(exc))
        traceback.print_exc()

        return (
            "Sorry, I am temporarily unable to connect to the AI "
            "service. Please try again."
        )

    except Exception as exc:
        print("AI UNEXPECTED ERROR:", repr(exc))
        traceback.print_exc()

        return (
            "Sorry, something went wrong while generating my response."
        )


# ================================================================
# BUSINESS API
# ================================================================

@app.route("/api/business", methods=["GET"])
def get_business():
    """
    Preserve the business profile endpoint used by the dashboard
    and AI Assistant.
    """

    business = {
        "name": os.environ.get(
            "BUSINESS_NAME",
            "NexaFlow AI Business"
        ),
        "owner_name": os.environ.get(
            "OWNER_NAME",
            ""
        ),
        "logo": os.environ.get(
            "BUSINESS_LOGO",
            ""
        )
    }

    # Try Supabase when configured.
    response = supabase_request(
        "GET",
        "businesses?select=*&limit=1"
    )

    if response is not None and response.ok:
        try:
            data = response.json()

            if isinstance(data, list) and data:
                db_business = data[0]

                for key in (
                    "name",
                    "business_name",
                    "owner_name",
                    "logo"
                ):
                    if key in db_business and db_business[key]:
                        if key == "business_name":
                            business["name"] = db_business[key]
                        else:
                            business[key] = db_business[key]

        except Exception as exc:
            print(
                "BUSINESS PARSE ERROR:",
                repr(exc)
            )

    return jsonify(business)


# ================================================================
# AI ASSISTANT API
# ================================================================

@app.route("/api/ai", methods=["POST"])
def ai_endpoint():
    body = get_json_body()

    question = (
        body.get("question")
        or body.get("message")
        or ""
    ).strip()

    conversation_context = body.get(
        "conversation_history"
    )

    print("AI ENDPOINT QUESTION:", question)

    answer = generate_ai_response(
        question,
        conversation_context
    )

    return jsonify({
        "success": True,
        "answer": answer,
        "response": answer,
        "timestamp": now_iso()
    })


# ================================================================
# CUSTOMER HELPERS
# ================================================================

def find_customer_by_phone(phone):
    phone = str(phone or "").strip()

    if not phone:
        return None

    # Check memory first.
    for customer in customers:
        if str(customer.get("phone", "")).strip() == phone:
            return customer

    # Check Supabase.
    if supabase_available():
        response = supabase_request(
            "GET",
            "customers",
            params={
                "phone": f"eq.{phone}",
                "select": "*",
                "limit": 1
            }
        )

        if response is not None and response.ok:
            try:
                data = response.json()

                if isinstance(data, list) and data:
                    return data[0]

            except Exception as exc:
                print(
                    "CUSTOMER LOOKUP PARSE ERROR:",
                    repr(exc)
                )

    return None


def create_or_update_customer(
    phone,
    name=None,
    last_message=None,
    ai_reply=None
):
    phone = str(phone or "").strip()

    if not phone:
        return None

    name = (
        str(name).strip()
        if name
        else "WhatsApp Customer"
    )

    existing = find_customer_by_phone(phone)

    if existing:
        customer_id = existing.get("id")

        update_data = {
            "phone": phone,
            "name": existing.get("name") or name,
            "updated_at": now_iso()
        }

        if last_message:
            update_data["message"] = last_message

        if ai_reply:
            update_data["ai_reply"] = ai_reply

        # Update Supabase record when possible.
        if customer_id and supabase_available():
            response = supabase_request(
                "PATCH",
                "customers",
                params={
                    "id": f"eq.{customer_id}"
                },
                json=update_data
            )

            if response is not None and response.ok:
                try:
                    data = response.json()

                    if isinstance(data, list) and data:
                        existing = data[0]

                except Exception:
                    pass

        # Update in-memory object.
        existing.update(update_data)

        return existing

    customer = {
        "id": str(uuid.uuid4()),
        "name": name,
        "phone": phone,
        "message": last_message or "",
        "ai_reply": ai_reply or "",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    if supabase_available():
        response = supabase_request(
            "POST",
            "customers",
            json=customer
        )

        if response is not None and response.ok:
            try:
                data = response.json()

                if isinstance(data, list) and data:
                    customer = data[0]

            except Exception as exc:
                print(
                    "CUSTOMER CREATE PARSE ERROR:",
                    repr(exc)
                )

    customers.append(customer)

    return customer


# ================================================================
# CUSTOMER API
# ================================================================

@app.route("/api/customers", methods=["GET"])
def get_customers():
    if supabase_available():
        response = supabase_request(
            "GET",
            "customers?select=*&order=created_at.desc"
        )

        if response is not None and response.ok:
            try:
                data = response.json()

                if isinstance(data, list):
                    return jsonify(data)

            except Exception:
                pass

    return jsonify(customers)


@app.route("/api/customers", methods=["POST"])
def save_customer():
    body = get_json_body()

    name = (
        body.get("name")
        or body.get("customer_name")
        or "Customer"
    )

    phone = (
        body.get("phone")
        or body.get("phone_number")
        or ""
    )

    message = (
        body.get("message")
        or ""
    )

    ai_reply = (
        body.get("ai_reply")
        or body.get("aiReply")
        or ""
    )

    customer = create_or_update_customer(
        phone=phone,
        name=name,
        last_message=message,
        ai_reply=ai_reply
    )

    return jsonify({
        "success": True,
        "customer": customer
    })


# ================================================================
# MESSAGE STORAGE
# ================================================================

def save_message(
    direction,
    phone,
    text,
    customer_id=None,
    whatsapp_message_id=None,
    ai_reply=None,
    message_type="text"
):
    message_record = {
        "id": str(uuid.uuid4()),
        "direction": direction,
        "phone": phone,
        "text": text,
        "customer_id": customer_id,
        "whatsapp_message_id": whatsapp_message_id,
        "ai_reply": ai_reply or "",
        "message_type": message_type,
        "created_at": now_iso()
    }

    if supabase_available():
        payload = dict(message_record)

        # Some existing schemas may not contain every optional
        # column. First try the complete record.
        response = supabase_request(
            "POST",
            "messages",
            json=payload
        )

        if response is not None and response.ok:
            try:
                data = response.json()

                if isinstance(data, list) and data:
                    message_record = data[0]

            except Exception:
                pass

        else:
            print(
                "MESSAGE SAVE WITH FULL PAYLOAD FAILED. "
                "Trying compatibility payload."
            )

            compatibility_payload = {
                "direction": direction,
                "phone": phone,
                "text": text,
                "customer_id": customer_id,
                "created_at": message_record["created_at"]
            }

            response2 = supabase_request(
                "POST",
                "messages",
                json=compatibility_payload
            )

            if response2 is not None and response2.ok:
                try:
                    data = response2.json()

                    if isinstance(data, list) and data:
                        message_record = data[0]

                except Exception:
                    pass

    messages.append(message_record)

    print(
        "MESSAGE STORED:",
        json.dumps(message_record, default=str)[:3000]
    )

    return message_record


@app.route("/api/messages", methods=["GET"])
def get_messages():
    if supabase_available():
        response = supabase_request(
            "GET",
            "messages?select=*&order=created_at.desc"
        )

        if response is not None and response.ok:
            try:
                data = response.json()

                if isinstance(data, list):
                    return jsonify(data)

            except Exception:
                pass

    return jsonify(messages)

# ================================================================
# WHATSAPP INTEGRATION HELPERS
# ================================================================

def find_whatsapp_integration(phone_number_id=None):
    """
    Find the WhatsApp integration belonging to the phone number ID.

    The lookup deliberately tries several common column names so that
    an existing NexaFlow database structure is not unnecessarily broken.
    """

    phone_number_id = str(
        phone_number_id or WHATSAPP_PHONE_NUMBER_ID or ""
    ).strip()

    print(
        "FIND WHATSAPP INTEGRATION:",
        phone_number_id,
        flush=True
    )

    if not phone_number_id:
        print(
            "WHATSAPP INTEGRATION ERROR: "
            "No phone number ID available.",
            flush=True
        )
        return None

    if not supabase_available():
        print(
            "WHATSAPP INTEGRATION ERROR: "
            "Supabase is not configured.",
            flush=True
        )
        return None

    # Try the likely table/column combinations used by the
    # existing NexaFlow application.
    attempts = [
        (
            "whatsapp_integrations",
            {
                "phone_number_id": f"eq.{phone_number_id}",
                "select": "*",
                "limit": 1
            }
        ),
        (
            "whatsapp_integrations",
            {
                "phoneNumberId": f"eq.{phone_number_id}",
                "select": "*",
                "limit": 1
            }
        ),
        (
            "whatsapp_integrations",
            {
                "meta_phone_number_id": f"eq.{phone_number_id}",
                "select": "*",
                "limit": 1
            }
        ),
        (
            "integrations",
            {
                "phone_number_id": f"eq.{phone_number_id}",
                "select": "*",
                "limit": 1
            }
        )
    ]

    for table, params in attempts:
        try:
            response = supabase_request(
                "GET",
                table,
                params=params
            )

            if response is None:
                continue

            if not response.ok:
                continue

            data = response.json()

            if isinstance(data, list) and data:
                integration = data[0]

                print(
                    "WHATSAPP INTEGRATION FOUND:",
                    json.dumps(
                        integration,
                        default=str
                    )[:4000],
                    flush=True
                )

                return integration

        except Exception as error:
            print(
                "INTEGRATION LOOKUP ERROR:",
                table,
                repr(error),
                flush=True
            )

    print(
        "NO WHATSAPP INTEGRATION FOUND:",
        phone_number_id,
        flush=True
    )

    return None


def whatsapp_message_exists(external_message_id):
    """
    Prevent Meta from causing duplicate customer messages when
    the same webhook is delivered more than once.
    """

    external_message_id = str(
        external_message_id or ""
    ).strip()

    if not external_message_id:
        return False

    with processed_whatsapp_message_lock:
        if external_message_id in processed_whatsapp_message_ids:
            return True

    if supabase_available():
        try:
            response = supabase_request(
                "GET",
                "messages",
                params={
                    "whatsapp_message_id":
                        f"eq.{external_message_id}",
                    "select": "id",
                    "limit": 1
                }
            )

            if response is not None and response.ok:
                data = response.json()

                if isinstance(data, list) and data:
                    with processed_whatsapp_message_lock:
                        processed_whatsapp_message_ids.add(
                            external_message_id
                        )

                    return True

        except Exception as error:
            print(
                "WHATSAPP DUPLICATE LOOKUP ERROR:",
                repr(error),
                flush=True
            )

    return False


def mark_whatsapp_message_processed(external_message_id):
    external_message_id = str(
        external_message_id or ""
    ).strip()

    if not external_message_id:
        return

    with processed_whatsapp_message_lock:
        processed_whatsapp_message_ids.add(
            external_message_id
        )


# ================================================================
# WHATSAPP DATABASE STORAGE
# ================================================================

def store_whatsapp_message(
    integration,
    sender_phone,
    sender_name,
    message_text,
    external_message_id
):
    """
    Store an incoming WhatsApp message and make sure a customer
    record exists.

    The integration's user_id is preserved whenever available.
    """

    sender_phone = str(
        sender_phone or ""
    ).strip()

    sender_name = str(
        sender_name or ""
    ).strip()

    message_text = str(
        message_text or ""
    ).strip()

    external_message_id = str(
        external_message_id or ""
    ).strip()

    if not sender_phone:
        print(
            "STORE WHATSAPP MESSAGE ERROR: "
            "sender phone is empty.",
            flush=True
        )
        return None

    if not message_text:
        print(
            "STORE WHATSAPP MESSAGE ERROR: "
            "message text is empty.",
            flush=True
        )
        return None

    print(
        "STORE WHATSAPP MESSAGE:",
        {
            "sender_phone": sender_phone,
            "sender_name": sender_name,
            "message": message_text,
            "external_id": external_message_id
        },
        flush=True
    )

    # ------------------------------------------------------------
    # CUSTOMER
    # ------------------------------------------------------------

    customer = find_customer_by_phone(
        sender_phone
    )

    if customer:
        customer_id = customer.get("id")

        customer = create_or_update_customer(
            phone=sender_phone,
            name=sender_name or customer.get("name"),
            last_message=message_text
        )

    else:
        customer = create_or_update_customer(
            phone=sender_phone,
            name=sender_name or "WhatsApp Customer",
            last_message=message_text
        )

    customer_id = (
        customer.get("id")
        if isinstance(customer, dict)
        else None
    )

    print(
        "WHATSAPP CUSTOMER:",
        customer,
        flush=True
    )

    # ------------------------------------------------------------
    # MESSAGE
    # ------------------------------------------------------------

    message_record = save_message(
        direction="incoming",
        phone=sender_phone,
        text=message_text,
        customer_id=customer_id,
        whatsapp_message_id=external_message_id,
        message_type="whatsapp"
    )

    mark_whatsapp_message_processed(
        external_message_id
    )

    return message_record


# ================================================================
# WHATSAPP AI CONTEXT
# ================================================================

def get_whatsapp_conversation_history(
    phone,
    limit=10
):
    """
    Retrieve recent messages for the WhatsApp customer.

    Failure to retrieve history must never prevent the AI from
    answering the current message.
    """

    phone = str(phone or "").strip()

    if not phone:
        return []

    history = []

    if supabase_available():
        try:
            response = supabase_request(
                "GET",
                "messages",
                params={
                    "phone": f"eq.{phone}",
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": limit
                }
            )

            if response is not None and response.ok:
                data = response.json()

                if isinstance(data, list):
                    # Database returns newest first.
                    data.reverse()

                    for item in data:
                        direction = str(
                            item.get("direction") or ""
                        ).lower()

                        text = str(
                            item.get("text") or ""
                        ).strip()

                        if not text:
                            continue

                        if direction == "incoming":
                            role = "user"

                        elif direction == "outgoing":
                            role = "assistant"

                        else:
                            continue

                        history.append({
                            "role": role,
                            "content": text
                        })

        except Exception as error:
            print(
                "WHATSAPP HISTORY ERROR:",
                repr(error),
                flush=True
            )

    return history


# ================================================================
# WHATSAPP META API
# ================================================================

def send_whatsapp_message(
    recipient_phone,
    message_text,
    phone_number_id=None,
    access_token=None
):
    """
    Send a text reply through Meta WhatsApp Cloud API.
    """

    recipient_phone = str(
        recipient_phone or ""
    ).strip()

    message_text = str(
        message_text or ""
    ).strip()

    phone_number_id = str(
        phone_number_id
        or WHATSAPP_PHONE_NUMBER_ID
        or ""
    ).strip()

    access_token = str(
        access_token
        or WHATSAPP_ACCESS_TOKEN
        or ""
    ).strip()

    if not recipient_phone:
        print(
            "WHATSAPP SEND ERROR: "
            "recipient phone is empty.",
            flush=True
        )
        return None

    if not message_text:
        print(
            "WHATSAPP SEND ERROR: "
            "message is empty.",
            flush=True
        )
        return None

    if not phone_number_id:
        print(
            "WHATSAPP SEND ERROR: "
            "phone number ID is missing.",
            flush=True
        )
        return None

    if not access_token:
        print(
            "WHATSAPP SEND ERROR: "
            "access token is missing.",
            flush=True
        )
        return None

    # Meta text messages should remain within the normal text
    # message size limit. Keep the complete response when possible.
    if len(message_text) > 4096:
        message_text = message_text[:4090] + "..."

    url = (
        "https://graph.facebook.com/v23.0/"
        f"{phone_number_id}/messages"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
        }
    }

    try:
        print(
            "========== WHATSAPP META SEND START ==========",
            flush=True
        )

        print(
            "META PHONE NUMBER ID:",
            phone_number_id,
            flush=True
        )

        print(
            "META RECIPIENT:",
            recipient_phone,
            flush=True
        )

        print(
            "META MESSAGE:",
            message_text[:4000],
            flush=True
        )

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(
            "META SEND HTTP STATUS:",
            response.status_code,
            flush=True
        )

        print(
            "META SEND RESPONSE:",
            response.text[:4000],
            flush=True
        )

        if not response.ok:
            print(
                "META WHATSAPP SEND FAILED.",
                flush=True
            )

            return None

        try:
            result = response.json()
        except Exception:
            result = {
                "raw_response":
                    response.text
            }

        print(
            "WHATSAPP META SEND SUCCESS:",
            result,
            flush=True
        )

        print(
            "========== WHATSAPP META SEND END ==========",
            flush=True
        )

        return result

    except requests.RequestException as error:
        print(
            "WHATSAPP META NETWORK ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return None

    except Exception as error:
        print(
            "WHATSAPP META SEND UNEXPECTED ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return None


# ================================================================
# WHATSAPP OUTGOING MESSAGE STORAGE
# ================================================================

def store_whatsapp_ai_reply(
    integration,
    incoming_message,
    reply_text,
    recipient_phone
):
    """
    Save the outgoing AI reply and update the customer's latest
    AI response.
    """

    reply_text = str(
        reply_text or ""
    ).strip()

    recipient_phone = str(
        recipient_phone or ""
    ).strip()

    if not reply_text:
        return None

    customer_id = None

    if isinstance(incoming_message, dict):
        customer_id = incoming_message.get(
            "customer_id"
        )

    outgoing = save_message(
        direction="outgoing",
        phone=recipient_phone,
        text=reply_text,
        customer_id=customer_id,
        message_type="whatsapp"
    )

    # Update customer with the latest AI reply.
    try:
        customer = find_customer_by_phone(
            recipient_phone
        )

        if customer:
            create_or_update_customer(
                phone=recipient_phone,
                name=customer.get("name"),
                ai_reply=reply_text
            )

    except Exception as error:
        print(
            "CUSTOMER AI REPLY UPDATE ERROR:",
            repr(error),
            flush=True
        )

    return outgoing


# ================================================================
# WHATSAPP AI WORKER
# ================================================================

def process_whatsapp_message_with_ai(
    integration,
    incoming_message
):
    """
    Complete asynchronous WhatsApp flow:

        incoming message
              ↓
        conversation history
              ↓
        OpenRouter
              ↓
        Meta WhatsApp reply
              ↓
        outgoing message storage
              ↓
        customer update
    """

    print(
        "============================================================",
        flush=True
    )

    print(
        "BACKGROUND WHATSAPP AI PROCESS START",
        flush=True
    )

    print(
        "============================================================",
        flush=True
    )

    try:
        if not isinstance(incoming_message, dict):
            print(
                "WORKER ERROR: incoming message is not a dictionary.",
                flush=True
            )
            return False

        sender_phone = str(
            incoming_message.get("phone") or ""
        ).strip()

        message_text = str(
            incoming_message.get("text") or ""
        ).strip()

        if not sender_phone:
            print(
                "WORKER ERROR: sender phone missing.",
                flush=True
            )
            return False

        if not message_text:
            print(
                "WORKER ERROR: message text missing.",
                flush=True
            )
            return False

        print(
            "WORKER PHONE:",
            sender_phone,
            flush=True
        )

        print(
            "WORKER MESSAGE:",
            message_text,
            flush=True
        )

        # --------------------------------------------------------
        # CONVERSATION HISTORY
        # --------------------------------------------------------

        conversation_history = (
            get_whatsapp_conversation_history(
                sender_phone,
                limit=10
            )
        )

        print(
            "WHATSAPP CONVERSATION HISTORY:",
            conversation_history,
            flush=True
        )

        # --------------------------------------------------------
        # AI
        # --------------------------------------------------------

        print(
            "STEP 1: GENERATING AI RESPONSE",
            flush=True
        )

        ai_reply = generate_ai_response(
            message_text,
            conversation_history
        )

        ai_reply = str(
            ai_reply or ""
        ).strip()

        if not ai_reply:
            print(
                "STEP 1 FAILED: AI returned empty response.",
                flush=True
            )
            return False

        print(
            "STEP 1 SUCCESS: AI generated:",
            ai_reply[:4000],
            flush=True
        )

        # --------------------------------------------------------
        # META WHATSAPP
        # --------------------------------------------------------

        integration_phone_number_id = (
            integration.get("phone_number_id")
            or integration.get("phoneNumberId")
            or integration.get("meta_phone_number_id")
            or WHATSAPP_PHONE_NUMBER_ID
        )

        integration_access_token = (
            integration.get("access_token")
            or integration.get("accessToken")
            or integration.get("whatsapp_access_token")
            or WHATSAPP_ACCESS_TOKEN
        )

        print(
            "STEP 2: SENDING AI RESPONSE THROUGH META",
            flush=True
        )

        meta_result = send_whatsapp_message(
            recipient_phone=sender_phone,
            message_text=ai_reply,
            phone_number_id=integration_phone_number_id,
            access_token=integration_access_token
        )

        if not meta_result:
            print(
                "STEP 2 FAILED: WhatsApp reply was not sent.",
                flush=True
            )
            return False

        print(
            "STEP 2 SUCCESS: WhatsApp reply sent.",
            flush=True
        )

        # --------------------------------------------------------
        # STORE OUTGOING RESPONSE
        # --------------------------------------------------------

        print(
            "STEP 3: SAVING OUTGOING MESSAGE",
            flush=True
        )

        outgoing = store_whatsapp_ai_reply(
            integration=integration,
            incoming_message=incoming_message,
            reply_text=ai_reply,
            recipient_phone=sender_phone
        )

        print(
            "STEP 3 SUCCESS: OUTGOING MESSAGE:",
            outgoing,
            flush=True
        )

        # --------------------------------------------------------
        # UPDATE INCOMING MESSAGE WITH AI REPLY
        # --------------------------------------------------------

        incoming_id = incoming_message.get("id")

        if incoming_id and supabase_available():
            try:
                response = supabase_request(
                    "PATCH",
                    "messages",
                    params={
                        "id":
                            f"eq.{incoming_id}"
                    },
                    json={
                        "ai_reply": ai_reply
                    }
                )

                if response is not None and response.ok:
                    print(
                        "INCOMING MESSAGE AI REPLY UPDATED.",
                        flush=True
                    )
                else:
                    print(
                        "INCOMING MESSAGE AI REPLY UPDATE FAILED.",
                        flush=True
                    )

            except Exception as error:
                print(
                    "INCOMING MESSAGE UPDATE ERROR:",
                    repr(error),
                    flush=True
                )

        print(
            "============================================================",
            flush=True
        )

        print(
            "BACKGROUND WHATSAPP AI PROCESS COMPLETE",
            flush=True
        )

        print(
            "============================================================",
            flush=True
        )

        return True

    except Exception as error:
        print(
            "BACKGROUND WHATSAPP AI PROCESS ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return False


def start_whatsapp_ai_thread(
    integration,
    incoming_message
):
    """
    Start WhatsApp AI processing without using a daemon thread.

    The non-daemon worker is intentional: Render should not treat the
    AI operation as disposable immediately after Flask returns 200.
    """

    try:
        if not integration:
            print(
                "THREAD START FAILED: integration missing.",
                flush=True
            )
            return False

        if not incoming_message:
            print(
                "THREAD START FAILED: incoming message missing.",
                flush=True
            )
            return False

        thread = threading.Thread(
            target=process_whatsapp_message_with_ai,
            args=(
                integration,
                incoming_message
            ),
            daemon=False,
            name="whatsapp-ai-worker"
        )

        thread.start()

        print(
            "WHATSAPP AI BACKGROUND THREAD STARTED:",
            thread.name,
            flush=True
        )

        return True

    except Exception as error:
        print(
            "FAILED TO START WHATSAPP AI THREAD:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return False


# ================================================================
# WHATSAPP WEBHOOK VERIFICATION
# ================================================================

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

    print(
        "========== WHATSAPP WEBHOOK VERIFY ==========",
        flush=True
    )

    print(
        "VERIFY MODE:",
        mode,
        flush=True
    )

    print(
        "VERIFY TOKEN RECEIVED:",
        bool(token),
        flush=True
    )

    if (
        mode == "subscribe"
        and token
        and WHATSAPP_VERIFY_TOKEN
        and token == WHATSAPP_VERIFY_TOKEN
    ):

        print(
            "WHATSAPP WEBHOOK VERIFICATION SUCCESSFUL.",
            flush=True
        )

        return challenge or "", 200

    print(
        "WHATSAPP WEBHOOK VERIFICATION FAILED.",
        flush=True
    )

    return "Forbidden", 403


# ================================================================
# WHATSAPP WEBHOOK
# ================================================================

@app.route(
    "/api/whatsapp/webhook",
    methods=["POST"]
)
def whatsapp_webhook():

    print(
        "========== WHATSAPP WEBHOOK START ==========",
        flush=True
    )

    print(
        "WEBHOOK METHOD:",
        request.method,
        flush=True
    )

    # ------------------------------------------------------------
    # PAYLOAD
    # ------------------------------------------------------------

    try:
        payload = request.get_json(
            silent=True
        ) or {}

    except Exception as error:
        print(
            "WHATSAPP PAYLOAD JSON ERROR:",
            repr(error),
            flush=True
        )

        return jsonify({
            "success": True
        }), 200

    print(
        "========== WHATSAPP PAYLOAD RECEIVED ==========",
        flush=True
    )

    print(
        json.dumps(
            payload,
            indent=2,
            default=str
        )[:12000],
        flush=True
    )

    # ------------------------------------------------------------
    # OBJECT
    # ------------------------------------------------------------

    if payload.get("object") != (
        "whatsapp_business_account"
    ):

        print(
            "WEBHOOK OBJECT IS NOT "
            "whatsapp_business_account:",
            payload.get("object"),
            flush=True
        )

        return jsonify({
            "success": True,
            "processed": 0
        }), 200

    entries = payload.get(
        "entry"
    ) or []

    processed = 0
    threads_started = 0
    status_events = 0
    errors = 0

    # ------------------------------------------------------------
    # ENTRIES
    # ------------------------------------------------------------

    for entry in entries:

        changes = (
            entry.get("changes")
            or []
        )

        for change in changes:

            try:
                value = (
                    change.get("value")
                    or {}
                )

                field = change.get(
                    "field"
                )

                print(
                    "WEBHOOK FIELD:",
                    field,
                    flush=True
                )

                metadata = (
                    value.get("metadata")
                    or {}
                )

                phone_number_id = str(
                    metadata.get(
                        "phone_number_id"
                    )
                    or ""
                ).strip()

                print(
                    "META PHONE NUMBER ID:",
                    phone_number_id,
                    flush=True
                )

                lookup_phone_number_id = (
                    phone_number_id
                    or WHATSAPP_PHONE_NUMBER_ID
                )

                integration = (
                    find_whatsapp_integration(
                        lookup_phone_number_id
                    )
                )

                if not integration:

                    print(
                        "NO INTEGRATION FOUND FOR "
                        "PHONE NUMBER ID:",
                        lookup_phone_number_id,
                        flush=True
                    )

                    errors += 1
                    continue

                print(
                    "MATCHED INTEGRATION:",
                    integration.get("id"),
                    flush=True
                )

                print(
                    "MATCHED USER:",
                    integration.get("user_id"),
                    flush=True
                )

                incoming_messages = (
                    value.get("messages")
                    or []
                )

                statuses = (
                    value.get("statuses")
                    or []
                )

                if statuses and not incoming_messages:

                    status_events += len(
                        statuses
                    )

                    print(
                        "STATUS EVENT RECEIVED:",
                        statuses,
                        flush=True
                    )

                    continue

                if not incoming_messages:

                    print(
                        "NO INBOUND MESSAGES "
                        "IN THIS WEBHOOK EVENT.",
                        flush=True
                    )

                    continue

                contacts = (
                    value.get("contacts")
                    or []
                )

                contact_names = {}

                for contact in contacts:

                    wa_id = str(
                        contact.get("wa_id")
                        or ""
                    ).strip()

                    profile = (
                        contact.get("profile")
                        or {}
                    )

                    profile_name = str(
                        profile.get("name")
                        or ""
                    ).strip()

                    if wa_id:
                        contact_names[
                            wa_id
                        ] = profile_name

                default_contact_name = ""

                if contacts:

                    default_contact_name = str(
                        (
                            contacts[0].get(
                                "profile"
                            )
                            or {}
                        ).get(
                            "name"
                        )
                        or ""
                    ).strip()

                # ------------------------------------------------
                # MESSAGES
                # ------------------------------------------------

                for incoming in incoming_messages:

                    try:

                        external_message_id = str(
                            incoming.get("id")
                            or ""
                        ).strip()

                        print(
                            "INCOMING META MESSAGE ID:",
                            external_message_id,
                            flush=True
                        )

                        if not external_message_id:

                            print(
                                "SKIPPING MESSAGE: "
                                "Meta message ID missing.",
                                flush=True
                            )

                            errors += 1
                            continue

                        if whatsapp_message_exists(
                            external_message_id
                        ):

                            print(
                                "DUPLICATE WHATSAPP MESSAGE:",
                                external_message_id,
                                flush=True
                            )

                            continue

                        sender_phone = str(
                            incoming.get("from")
                            or ""
                        ).strip()

                        message_type = str(
                            incoming.get("type")
                            or ""
                        ).strip().lower()

                        message_text = ""

                        # ------------------------------------------------
                        # TEXT
                        # ------------------------------------------------

                        if message_type == "text":

                            message_text = str(
                                (
                                    incoming.get(
                                        "text"
                                    )
                                    or {}
                                ).get(
                                    "body"
                                )
                                or ""
                            ).strip()

                        # ------------------------------------------------
                        # BUTTON
                        # ------------------------------------------------

                        elif message_type == "button":

                            button = (
                                incoming.get(
                                    "button"
                                )
                                or {}
                            )

                            message_text = str(
                                button.get(
                                    "text"
                                )
                                or button.get(
                                    "payload"
                                )
                                or ""
                            ).strip()

                        # ------------------------------------------------
                        # INTERACTIVE
                        # ------------------------------------------------

                        elif message_type == "interactive":

                            interactive = (
                                incoming.get(
                                    "interactive"
                                )
                                or {}
                            )

                            interactive_type = str(
                                interactive.get(
                                    "type"
                                )
                                or ""
                            ).strip().lower()

                            if (
                                interactive_type
                                == "button_reply"
                            ):

                                reply = (
                                    interactive.get(
                                        "button_reply"
                                    )
                                    or {}
                                )

                                message_text = str(
                                    reply.get(
                                        "title"
                                    )
                                    or reply.get(
                                        "id"
                                    )
                                    or ""
                                ).strip()

                            elif (
                                interactive_type
                                == "list_reply"
                            ):

                                reply = (
                                    interactive.get(
                                        "list_reply"
                                    )
                                    or {}
                                )

                                message_text = str(
                                    reply.get(
                                        "title"
                                    )
                                    or reply.get(
                                        "description"
                                    )
                                    or reply.get(
                                        "id"
                                    )
                                    or ""
                                ).strip()

                            else:

                                message_text = (
                                    "[interactive message]"
                                )

                        # ------------------------------------------------
                        # OTHER MESSAGE TYPES
                        # ------------------------------------------------

                        else:

                            message_text = (
                                "["
                                + message_type
                                + " message]"
                            )

                        sender_name = (
                            contact_names.get(
                                sender_phone
                            )
                            or default_contact_name
                        ).strip()

                        print(
                            "SENDER:",
                            sender_phone,
                            flush=True
                        )

                        print(
                            "CUSTOMER NAME:",
                            sender_name,
                            flush=True
                        )

                        print(
                            "MESSAGE TYPE:",
                            message_type,
                            flush=True
                        )

                        print(
                            "MESSAGE TEXT:",
                            message_text,
                            flush=True
                        )

                        if (
                            not sender_phone
                            or not message_text
                        ):

                            print(
                                "SKIPPING MESSAGE: "
                                "sender phone or text empty.",
                                flush=True
                            )

                            errors += 1
                            continue

                        # ------------------------------------------------
                        # STORE INCOMING MESSAGE
                        # ------------------------------------------------

                        stored = (
                            store_whatsapp_message(
                                integration=integration,
                                sender_phone=sender_phone,
                                sender_name=sender_name,
                                message_text=message_text,
                                external_message_id=
                                    external_message_id
                            )
                        )

                        if not stored:

                            print(
                                "FAILED TO STORE INCOMING "
                                "WHATSAPP MESSAGE:",
                                external_message_id,
                                flush=True
                            )

                            errors += 1
                            continue

                        processed += 1

                        print(
                            "INCOMING MESSAGE STORED:",
                            stored,
                            flush=True
                        )

                        # ------------------------------------------------
                        # START AI
                        # ------------------------------------------------

                        thread_started = (
                            start_whatsapp_ai_thread(
                                integration,
                                stored
                            )
                        )

                        print(
                            "AI THREAD STARTED:",
                            thread_started,
                            flush=True
                        )

                        if thread_started:
                            threads_started += 1
                        else:
                            errors += 1

                    except Exception as error:

                        errors += 1

                        print(
                            "WHATSAPP MESSAGE PROCESSING ERROR:",
                            repr(error),
                            flush=True
                        )

                        traceback.print_exc()

            except Exception as error:

                errors += 1

                print(
                    "WHATSAPP CHANGE PROCESSING ERROR:",
                    repr(error),
                    flush=True
                )

                traceback.print_exc()

    print(
        "========== WHATSAPP WEBHOOK END ==========",
        flush=True
    )

    print(
        "WEBHOOK SUMMARY:",
        {
            "processed": processed,
            "ai_threads_started":
                threads_started,
            "status_events":
                status_events,
            "errors":
                errors
        },
        flush=True
    )

    return jsonify({
        "success": True,
        "processed": processed,
        "ai_threads_started":
            threads_started,
        "status_events":
            status_events,
        "errors":
            errors
    }), 200


# ================================================================
# REPORTS
# ================================================================

@app.route(
    "/api/reports",
    methods=["GET"]
)
def get_reports():

    report = {
        "success": True,
        "total_customers": 0,
        "total_messages": 0,
        "total_ai_replies": 0
    }

    try:

        customer_data = customers

        message_data = messages

        if supabase_available():

            customer_response = (
                supabase_request(
                    "GET",
                    "customers",
                    params={
                        "select": "*",
                        "order":
                            "created_at.desc"
                    }
                )
            )

            if (
                customer_response
                is not None
                and customer_response.ok
            ):

                try:

                    data = (
                        customer_response.json()
                    )

                    if isinstance(data, list):
                        customer_data = data

                except Exception:
                    pass

            message_response = (
                supabase_request(
                    "GET",
                    "messages",
                    params={
                        "select": "*",
                        "order":
                            "created_at.desc"
                    }
                )
            )

            if (
                message_response
                is not None
                and message_response.ok
            ):

                try:

                    data = (
                        message_response.json()
                    )

                    if isinstance(data, list):
                        message_data = data

                except Exception:
                    pass

        report["total_customers"] = (
            len(customer_data)
        )

        report["total_messages"] = (
            len(message_data)
        )

        report["total_ai_replies"] = len([
            item
            for item in message_data
            if (
                str(
                    item.get(
                        "direction",
                        ""
                    )
                ).lower()
                == "outgoing"
            )
        ])

        report["customers"] = (
            customer_data
        )

        report["messages"] = (
            message_data
        )

        return jsonify(report)

    except Exception as error:

        print(
            "REPORTS ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ================================================================
# HEALTH CHECK
# ================================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "status": "ok",
        "service": "NexaFlow AI",
        "timestamp": now_iso(),
        "whatsapp_webhook": True,
        "whatsapp_ai": True,
        "ai_configured":
            bool(OPENROUTER_API_KEY),
        "supabase_configured":
            supabase_available(),
        "whatsapp_configured":
            bool(
                WHATSAPP_ACCESS_TOKEN
                and WHATSAPP_PHONE_NUMBER_ID
            )
    })


# ================================================================
# APPLICATION START
# ================================================================

if __name__ == "__main__":

    print(
        "================================================",
        flush=True
    )

    print(
        "NexaFlow AI starting...",
        flush=True
    )

    print(
        "Port:",
        PORT,
        flush=True
    )

    print(
        "WhatsApp AI background threading: ENABLED",
        flush=True
    )

    print(
        "WhatsApp webhook handler: "
        "ACTIVE / ROBUST PARSER ENABLED",
        flush=True
    )

    print(
        "WhatsApp phone number ID configured:",
        bool(WHATSAPP_PHONE_NUMBER_ID),
        flush=True
    )

    print(
        "WhatsApp access token configured:",
        bool(WHATSAPP_ACCESS_TOKEN),
        flush=True
    )

    print(
        "OpenRouter API key configured:",
        bool(OPENROUTER_API_KEY),
        flush=True
    )

    print(
        "Supabase key configured:",
        bool(SUPABASE_KEY),
        flush=True
    )

    print(
        "================================================",
        flush=True
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
