from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import requests
import os
import json
import threading
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

print("=" * 60, flush=True)
print("NexaFlow AI starting...", flush=True)
print(f"Port: {PORT}", flush=True)
print("WhatsApp AI background threading: ENABLED", flush=True)
print("WhatsApp webhook handler: ROBUST MODE ENABLED", flush=True)
print("=" * 60, flush=True)

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

print("Environment diagnostics:", flush=True)
print("SUPABASE_URL configured:", bool(SUPABASE_URL), flush=True)
print("SUPABASE_KEY configured:", bool(SUPABASE_KEY), flush=True)
print("OPENROUTER_API_KEY configured:", bool(OPENROUTER_API_KEY), flush=True)
print("WHATSAPP_ACCESS_TOKEN configured:", bool(WHATSAPP_ACCESS_TOKEN), flush=True)
print("WHATSAPP_PHONE_NUMBER_ID configured:", bool(WHATSAPP_PHONE_NUMBER_ID), flush=True)
print("WHATSAPP_VERIFY_TOKEN configured:", bool(WHATSAPP_VERIFY_TOKEN), flush=True)
print("OPENROUTER_MODEL:", OPENROUTER_MODEL, flush=True)

# ================================================================
# MEMORY STORAGE
# ================================================================

customers = []
messages = []

processed_whatsapp_message_ids = set()
processed_whatsapp_message_lock = threading.Lock()

# ================================================================
# GENERAL HELPERS
# ================================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_json_body():
    try:
        return request.get_json(silent=True) or {}
    except Exception:
        return {}


def supabase_available():
    return bool(SUPABASE_URL and SUPABASE_KEY)


def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


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
            f"SUPABASE {method} {endpoint}: {response.status_code}",
            flush=True
        )

        if response.text:
            print(
                "SUPABASE RESPONSE:",
                response.text[:2000],
                flush=True
            )

        return response

    except Exception as error:
        print(
            "SUPABASE REQUEST ERROR:",
            repr(error),
            flush=True
        )
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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "NexaFlow AI",
        "timestamp": now_iso(),
        "whatsapp_webhook": True,
        "whatsapp_ai": True,
        "ai_configured": bool(OPENROUTER_API_KEY),
        "supabase_configured": supabase_available(),
        "whatsapp_configured": bool(
            WHATSAPP_ACCESS_TOKEN
            and WHATSAPP_PHONE_NUMBER_ID
        )
    })


# ================================================================
# AI SERVICE
# ================================================================

def generate_ai_response(question, conversation_context=None):
    question = str(question or "").strip()

    if not question:
        return "Please send me a message and I will be happy to help."

    if not OPENROUTER_API_KEY:
        print(
            "AI ERROR: OPENROUTER_API_KEY is not configured.",
            flush=True
        )
        return (
            "Sorry, my AI service is not configured at the moment. "
            "Please try again later."
        )

    messages_payload = []

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
        print("=" * 50, flush=True)
        print("AI REQUEST START", flush=True)
        print("AI MODEL:", OPENROUTER_MODEL, flush=True)
        print("AI QUESTION:", question[:2000], flush=True)

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )

        print(
            "AI HTTP STATUS:",
            response.status_code,
            flush=True
        )

        print(
            "AI RAW RESPONSE:",
            response.text[:4000],
            flush=True
        )

        if not response.ok:
            print(
                "AI REQUEST FAILED:",
                response.status_code,
                flush=True
            )

            return (
                "Sorry, I could not generate a response right now. "
                "Please try again."
            )

        data = response.json()

        choices = data.get("choices") or []

        if not choices:
            print(
                "AI ERROR: No choices returned.",
                flush=True
            )
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
            print(
                "AI ERROR: Empty AI answer.",
                flush=True
            )
            return (
                "Sorry, I could not generate a response right now."
            )

        print(
            "AI SUCCESS:",
            answer[:4000],
            flush=True
        )
        print("=" * 50, flush=True)

        return answer

    except requests.RequestException as error:
        print(
            "AI NETWORK ERROR:",
            repr(error),
            flush=True
        )
        traceback.print_exc()

        return (
            "Sorry, I am temporarily unable to connect to the AI "
            "service. Please try again."
        )

    except Exception as error:
        print(
            "AI UNEXPECTED ERROR:",
            repr(error),
            flush=True
        )
        traceback.print_exc()

        return (
            "Sorry, something went wrong while generating my response."
        )


# ================================================================
# BUSINESS API
# ================================================================

@app.route("/api/business", methods=["GET"])
def get_business():
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

    response = supabase_request(
        "GET",
        "businesses?select=*&limit=1"
    )

    if response is not None and response.ok:
        try:
            data = response.json()

            if isinstance(data, list) and data:
                db_business = data[0]

                if db_business.get("name"):
                    business["name"] = db_business["name"]

                if db_business.get("business_name"):
                    business["name"] = db_business["business_name"]

                if db_business.get("owner_name"):
                    business["owner_name"] = db_business["owner_name"]

                if db_business.get("logo"):
                    business["logo"] = db_business["logo"]

        except Exception as error:
            print(
                "BUSINESS PARSE ERROR:",
                repr(error),
                flush=True
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

    print(
        "AI ENDPOINT QUESTION:",
        question,
        flush=True
    )

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
# CUSTOMER FUNCTIONS
# ================================================================

def find_customer_by_phone(phone):
    phone = str(phone or "").strip()

    if not phone:
        return None

    for customer in customers:
        if str(
            customer.get("phone", "")
        ).strip() == phone:
            return customer

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

            except Exception as error:
                print(
                    "CUSTOMER LOOKUP ERROR:",
                    repr(error),
                    flush=True
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

    name = str(
        name or "WhatsApp Customer"
    ).strip()

    existing = find_customer_by_phone(phone)

    if existing:
        update_data = {
            "phone": phone,
            "name": existing.get("name") or name,
            "updated_at": now_iso()
        }

        if last_message:
            update_data["message"] = last_message

        if ai_reply:
            update_data["ai_reply"] = ai_reply

        customer_id = existing.get("id")

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

            except Exception:
                pass
        else:
            print(
                "CUSTOMER SUPABASE SAVE FAILED - "
                "keeping customer in memory.",
                flush=True
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

    message = body.get("message") or ""

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
    created_at = now_iso()

    message_record = {
        "id": str(uuid.uuid4()),
        "direction": direction,
        "phone": str(phone or "").strip(),
        "text": str(text or "").strip(),
        "customer_id": customer_id,
        "whatsapp_message_id": whatsapp_message_id,
        "ai_reply": ai_reply or "",
        "message_type": message_type,
        "created_at": created_at
    }

    saved_to_supabase = False

    if supabase_available():
        full_payload = dict(message_record)

        response = supabase_request(
            "POST",
            "messages",
            json=full_payload
        )

        if response is not None and response.ok:
            saved_to_supabase = True

            try:
                data = response.json()

                if isinstance(data, list) and data:
                    message_record = data[0]

            except Exception:
                pass

        else:
            print(
                "FULL MESSAGE SAVE FAILED.",
                flush=True
            )

            # Compatibility payload for older messages table schemas.
            compatibility_payload = {
                "direction": direction,
                "phone": str(phone or "").strip(),
                "text": str(text or "").strip(),
                "customer_id": customer_id,
                "created_at": created_at
            }

            response2 = supabase_request(
                "POST",
                "messages",
                json=compatibility_payload
            )

            if response2 is not None and response2.ok:
                saved_to_supabase = True

                try:
                    data = response2.json()

                    if isinstance(data, list) and data:
                        message_record = data[0]

                except Exception:
                    pass

    messages.append(message_record)

    print(
        "MESSAGE STORED:",
        json.dumps(
            message_record,
            default=str
        )[:3000],
        flush=True
    )

    print(
        "MESSAGE SAVED TO SUPABASE:",
        saved_to_supabase,
        flush=True
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
# WHATSAPP INTEGRATION
# ================================================================

def find_whatsapp_integration(phone_number_id=None):
    phone_number_id = str(
        phone_number_id
        or WHATSAPP_PHONE_NUMBER_ID
        or ""
    ).strip()

    print(
        "FIND WHATSAPP INTEGRATION:",
        phone_number_id,
        flush=True
    )

    if not phone_number_id:
        return None

    if supabase_available():
        attempts = [
            (
                "whatsapp_integrations",
                {
                    "phone_number_id":
                        f"eq.{phone_number_id}",
                    "select": "*",
                    "limit": 1
                }
            ),
            (
                "whatsapp_integrations",
                {
                    "phoneNumberId":
                        f"eq.{phone_number_id}",
                    "select": "*",
                    "limit": 1
                }
            ),
            (
                "whatsapp_integrations",
                {
                    "meta_phone_number_id":
                        f"eq.{phone_number_id}",
                    "select": "*",
                    "limit": 1
                }
            ),
            (
                "integrations",
                {
                    "phone_number_id":
                        f"eq.{phone_number_id}",
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

                if response is None or not response.ok:
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
        "NO DATABASE WHATSAPP INTEGRATION FOUND.",
        flush=True
    )

    # IMPORTANT:
    # We no longer stop WhatsApp processing here.
    # The environment variables are sufficient for Meta API.
    fallback = {
        "id": "environment-whatsapp-integration",
        "user_id": None,
        "phone_number_id": phone_number_id
            or WHATSAPP_PHONE_NUMBER_ID,
        "access_token": WHATSAPP_ACCESS_TOKEN
    }

    if (
        fallback["phone_number_id"]
        and fallback["access_token"]
    ):
        print(
            "USING ENVIRONMENT WHATSAPP CONFIGURATION.",
            flush=True
        )
        return fallback

    print(
        "WHATSAPP ENVIRONMENT CONFIGURATION IS INCOMPLETE.",
        flush=True
    )

    return None


# ================================================================
# WHATSAPP DUPLICATE PROTECTION
# ================================================================

def whatsapp_message_exists(external_message_id):
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
# STORE INCOMING WHATSAPP MESSAGE
# ================================================================

def store_whatsapp_message(
    integration,
    sender_phone,
    sender_name,
    message_text,
    external_message_id
):
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
            "STORE WHATSAPP ERROR: sender phone empty.",
            flush=True
        )
        return None

    if not message_text:
        print(
            "STORE WHATSAPP ERROR: message text empty.",
            flush=True
        )
        return None

    print(
        "=" * 60,
        flush=True
    )
    print(
        "STORING INCOMING WHATSAPP MESSAGE",
        flush=True
    )
    print(
        "PHONE:",
        sender_phone,
        flush=True
    )
    print(
        "NAME:",
        sender_name,
        flush=True
    )
    print(
        "TEXT:",
        message_text,
        flush=True
    )
    print(
        "META ID:",
        external_message_id,
        flush=True
    )
    print(
        "=" * 60,
        flush=True
    )

    customer = create_or_update_customer(
        phone=sender_phone,
        name=sender_name or "WhatsApp Customer",
        last_message=message_text
    )

    customer_id = None

    if isinstance(customer, dict):
        customer_id = customer.get("id")

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
# WHATSAPP CONVERSATION HISTORY
# ================================================================

def get_whatsapp_conversation_history(
    phone,
    limit=10
):
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

    else:
        # Memory fallback.
        local_items = [
            item
            for item in messages
            if str(
                item.get("phone", "")
            ).strip() == phone
        ]

        local_items = local_items[-limit:]

        for item in local_items:
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

    return history


# ================================================================
# SEND WHATSAPP MESSAGE THROUGH META
# ================================================================

def send_whatsapp_message(
    recipient_phone,
    message_text,
    phone_number_id=None,
    access_token=None
):
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
            "WHATSAPP SEND ERROR: recipient empty.",
            flush=True
        )
        return None

    if not message_text:
        print(
            "WHATSAPP SEND ERROR: message empty.",
            flush=True
        )
        return None

    if not phone_number_id:
        print(
            "WHATSAPP SEND ERROR: phone number ID missing.",
            flush=True
        )
        return None

    if not access_token:
        print(
            "WHATSAPP SEND ERROR: access token missing.",
            flush=True
        )
        return None

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
        print("=" * 60, flush=True)
        print(
            "WHATSAPP META SEND START",
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
            print("=" * 60, flush=True)
            return None

        try:
            result = response.json()
        except Exception:
            result = {
                "raw_response": response.text
            }

        print(
            "WHATSAPP META SEND SUCCESS:",
            result,
            flush=True
        )
        print("=" * 60, flush=True)

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
# STORE OUTGOING AI REPLY
# ================================================================

def store_whatsapp_ai_reply(
    incoming_message,
    reply_text,
    recipient_phone
):
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
    print("=" * 70, flush=True)
    print(
        "BACKGROUND WHATSAPP AI PROCESS START",
        flush=True
    )
    print("=" * 70, flush=True)

    try:
        if not isinstance(incoming_message, dict):
            print(
                "WORKER ERROR: incoming message invalid.",
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
        # HISTORY
        # --------------------------------------------------------

        conversation_history = (
            get_whatsapp_conversation_history(
                sender_phone,
                limit=10
            )
        )

        print(
            "WHATSAPP HISTORY:",
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
                "STEP 1 FAILED: empty AI response.",
                flush=True
            )
            return False

        print(
            "STEP 1 SUCCESS:",
            ai_reply[:4000],
            flush=True
        )

        # --------------------------------------------------------
        # META CONFIGURATION
        # --------------------------------------------------------

        integration = (
            integration
            if isinstance(integration, dict)
            else {}
        )

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
            "RESOLVED META PHONE NUMBER ID:",
            bool(integration_phone_number_id),
            flush=True
        )

        print(
            "RESOLVED META ACCESS TOKEN:",
            bool(integration_access_token),
            flush=True
        )

        # --------------------------------------------------------
        # SEND
        # --------------------------------------------------------

        print(
            "STEP 2: SENDING AI RESPONSE TO WHATSAPP",
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
                "STEP 2 FAILED: META DID NOT SEND MESSAGE.",
                flush=True
            )
            return False

        print(
            "STEP 2 SUCCESS: META SENT MESSAGE.",
            flush=True
        )

        # --------------------------------------------------------
        # STORE OUTGOING
        # --------------------------------------------------------

        print(
            "STEP 3: STORING AI RESPONSE",
            flush=True
        )

        outgoing = store_whatsapp_ai_reply(
            incoming_message=incoming_message,
            reply_text=ai_reply,
            recipient_phone=sender_phone
        )

        print(
            "STEP 3 SUCCESS:",
            outgoing,
            flush=True
        )

        # --------------------------------------------------------
        # UPDATE INCOMING RECORD
        # --------------------------------------------------------

        incoming_id = incoming_message.get("id")

        if incoming_id and supabase_available():
            try:
                response = supabase_request(
                    "PATCH",
                    "messages",
                    params={
                        "id": f"eq.{incoming_id}"
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

        print("=" * 70, flush=True)
        print(
            "BACKGROUND WHATSAPP AI PROCESS COMPLETE",
            flush=True
        )
        print("=" * 70, flush=True)

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
    try:
        if not incoming_message:
            print(
                "THREAD START FAILED: incoming message missing.",
                flush=True
            )
            return False

        thread = threading.Thread(
            target=process_whatsapp_message_with_ai,
            args=(
                integration or {},
                incoming_message
            ),
            daemon=True,
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
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("=" * 60, flush=True)
    print(
        "WHATSAPP WEBHOOK VERIFY",
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
    print("=" * 70, flush=True)
    print(
        "WHATSAPP WEBHOOK START",
        flush=True
    )
    print("=" * 70, flush=True)

    try:
        payload = request.get_json(
            silent=True
        ) or {}
    except Exception as error:
        print(
            "WEBHOOK JSON ERROR:",
            repr(error),
            flush=True
        )

        return jsonify({
            "success": True
        }), 200

    print(
        "WHATSAPP PAYLOAD:",
        json.dumps(
            payload,
            indent=2,
            default=str
        )[:15000],
        flush=True
    )

    if payload.get("object") != "whatsapp_business_account":
        print(
            "WEBHOOK OBJECT:",
            payload.get("object"),
            flush=True
        )

        return jsonify({
            "success": True,
            "processed": 0
        }), 200

    entries = payload.get("entry") or []

    processed = 0
    threads_started = 0
    status_events = 0
    errors = 0

    for entry in entries:
        changes = entry.get("changes") or []

        for change in changes:
            try:
                value = change.get("value") or {}

                field = change.get("field")

                print(
                    "WEBHOOK FIELD:",
                    field,
                    flush=True
                )

                metadata = value.get("metadata") or {}

                phone_number_id = str(
                    metadata.get("phone_number_id")
                    or ""
                ).strip()

                print(
                    "WEBHOOK PHONE NUMBER ID:",
                    phone_number_id,
                    flush=True
                )

                # ------------------------------------------------
                # RESOLVE WHATSAPP CONFIGURATION
                # ------------------------------------------------

                integration = find_whatsapp_integration(
                    phone_number_id
                    or WHATSAPP_PHONE_NUMBER_ID
                )

                # IMPORTANT:
                # Even when database integration is missing,
                # continue using environment configuration.
                if not integration:
                    integration = {
                        "phone_number_id":
                            phone_number_id
                            or WHATSAPP_PHONE_NUMBER_ID,
                        "access_token":
                            WHATSAPP_ACCESS_TOKEN
                    }

                    print(
                        "USING DIRECT ENVIRONMENT WHATSAPP CONFIG.",
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

                # ------------------------------------------------
                # STATUS EVENTS
                # ------------------------------------------------

                if statuses:
                    status_events += len(statuses)

                    print(
                        "WHATSAPP STATUS EVENT:",
                        json.dumps(
                            statuses,
                            default=str
                        )[:5000],
                        flush=True
                    )

                # A status webhook does not contain a customer
                # message, so simply continue.
                if not incoming_messages:
                    print(
                        "NO INCOMING CUSTOMER MESSAGE "
                        "IN THIS EVENT.",
                        flush=True
                    )
                    continue

                # ------------------------------------------------
                # CONTACTS
                # ------------------------------------------------

                contacts = value.get("contacts") or []

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
                        contact_names[wa_id] = profile_name

                # ------------------------------------------------
                # PROCESS MESSAGES
                # ------------------------------------------------

                for incoming in incoming_messages:
                    try:
                        external_message_id = str(
                            incoming.get("id")
                            or ""
                        ).strip()

                        print(
                            "=" * 50,
                            flush=True
                        )

                        print(
                            "INCOMING META MESSAGE ID:",
                            external_message_id,
                            flush=True
                        )

                        if not external_message_id:
                            print(
                                "MESSAGE SKIPPED: "
                                "META ID missing.",
                                flush=True
                            )

                            errors += 1
                            continue

                        if whatsapp_message_exists(
                            external_message_id
                        ):
                            print(
                                "DUPLICATE MESSAGE:",
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
                            text_object = (
                                incoming.get("text")
                                or {}
                            )

                            message_text = str(
                                text_object.get("body")
                                or ""
                            ).strip()

                        # ------------------------------------------------
                        # BUTTON
                        # ------------------------------------------------

                        elif message_type == "button":
                            button = (
                                incoming.get("button")
                                or {}
                            )

                            message_text = str(
                                button.get("text")
                                or button.get("payload")
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
                                interactive.get("type")
                                or ""
                            ).strip().lower()

                            if interactive_type == "button_reply":
                                reply = (
                                    interactive.get(
                                        "button_reply"
                                    )
                                    or {}
                                )

                                message_text = str(
                                    reply.get("title")
                                    or reply.get("id")
                                    or ""
                                ).strip()

                            elif interactive_type == "list_reply":
                                reply = (
                                    interactive.get(
                                        "list_reply"
                                    )
                                    or {}
                                )

                                message_text = str(
                                    reply.get("title")
                                    or reply.get("description")
                                    or reply.get("id")
                                    or ""
                                ).strip()

                        # ------------------------------------------------
                        # OTHER TYPES
                        # ------------------------------------------------

                        else:
                            message_text = (
                                f"[{message_type} message]"
                            )

                        sender_name = (
                            contact_names.get(
                                sender_phone
                            )
                            or ""
                        ).strip()

                        print(
                            "SENDER PHONE:",
                            sender_phone,
                            flush=True
                        )

                        print(
                            "SENDER NAME:",
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

                        if not sender_phone:
                            print(
                                "MESSAGE SKIPPED: "
                                "sender phone empty.",
                                flush=True
                            )

                            errors += 1
                            continue

                        if not message_text:
                            print(
                                "MESSAGE SKIPPED: "
                                "message text empty.",
                                flush=True
                            )

                            errors += 1
                            continue

                        # ------------------------------------------------
                        # STORE MESSAGE
                        # ------------------------------------------------

                        stored = store_whatsapp_message(
                            integration=integration,
                            sender_phone=sender_phone,
                            sender_name=sender_name,
                            message_text=message_text,
                            external_message_id=
                                external_message_id
                        )

                        if not stored:
                            print(
                                "FAILED TO STORE INCOMING MESSAGE.",
                                flush=True
                            )

                            errors += 1
                            continue

                        processed += 1

                        print(
                            "INCOMING MESSAGE STORED SUCCESSFULLY:",
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
                            "INDIVIDUAL WHATSAPP MESSAGE ERROR:",
                            repr(error),
                            flush=True
                        )

                        traceback.print_exc()

            except Exception as error:
                errors += 1

                print(
                    "WEBHOOK CHANGE ERROR:",
                    repr(error),
                    flush=True
                )

                traceback.print_exc()

    print("=" * 70, flush=True)
    print(
        "WHATSAPP WEBHOOK END",
        flush=True
    )
    print(
        "WEBHOOK SUMMARY:",
        {
            "processed": processed,
            "ai_threads_started": threads_started,
            "status_events": status_events,
            "errors": errors
        },
        flush=True
    )
    print("=" * 70, flush=True)

    return jsonify({
        "success": True,
        "processed": processed,
        "ai_threads_started": threads_started,
        "status_events": status_events,
        "errors": errors
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
            customer_response = supabase_request(
                "GET",
                "customers",
                params={
                    "select": "*",
                    "order": "created_at.desc"
                }
            )

            if (
                customer_response is not None
                and customer_response.ok
            ):
                try:
                    data = customer_response.json()

                    if isinstance(data, list):
                        customer_data = data

                except Exception:
                    pass

            message_response = supabase_request(
                "GET",
                "messages",
                params={
                    "select": "*",
                    "order": "created_at.desc"
                }
            )

            if (
                message_response is not None
                and message_response.ok
            ):
                try:
                    data = message_response.json()

                    if isinstance(data, list):
                        message_data = data

                except Exception:
                    pass

        report["total_customers"] = len(
            customer_data
        )

        report["total_messages"] = len(
            message_data
        )

        report["total_ai_replies"] = len([
            item
            for item in message_data
            if str(
                item.get("direction", "")
            ).lower() == "outgoing"
        ])

        report["customers"] = customer_data
        report["messages"] = message_data

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
# APPLICATION START
# ================================================================

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("NexaFlow AI starting...", flush=True)
    print("Port:", PORT, flush=True)
    print(
        "WhatsApp AI background threading: ENABLED",
        flush=True
    )
    print(
        "WhatsApp webhook handler: ACTIVE",
        flush=True
    )
    print(
        "WhatsApp environment configuration:",
        bool(
            WHATSAPP_ACCESS_TOKEN
            and WHATSAPP_PHONE_NUMBER_ID
        ),
        flush=True
    )
    print(
        "OpenRouter configuration:",
        bool(OPENROUTER_API_KEY),
        flush=True
    )
    print(
        "Supabase configuration:",
        supabase_available(),
        flush=True
    )
    print("=" * 60, flush=True)

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
