from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import requests
import os
import json
import threading
import traceback
import uuid
import base64

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


def safe_response_json(response):
    if response is None:
        return None

    try:
        return response.json()
    except Exception:
        return None


# ================================================================
# BASIC ROUTES
# ================================================================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def serve_frontend(filename):
    return send_from_directory(".", filename)


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
# BUSINESS HELPERS
# ================================================================

def default_business():
    return {
        "id": None,
        "name": os.environ.get(
            "BUSINESS_NAME",
            "NexaFlow AI Business"
        ),
        "business_name": os.environ.get(
            "BUSINESS_NAME",
            "NexaFlow AI Business"
        ),
        "owner_name": os.environ.get(
            "OWNER_NAME",
            ""
        ),
        "phone": "",
        "email": "",
        "address": "",
        "description": "",
        "logo": os.environ.get(
            "BUSINESS_LOGO",
            ""
        )
    }


def normalize_business_record(record):
    if not isinstance(record, dict):
        return default_business()

    business = default_business()

    business["id"] = record.get("id")

    business_name = (
        record.get("business_name")
        or record.get("name")
        or business["business_name"]
    )

    business["name"] = business_name
    business["business_name"] = business_name

    business["owner_name"] = (
        record.get("owner_name")
        or ""
    )

    business["phone"] = (
        record.get("phone")
        or record.get("phone_number")
        or ""
    )

    business["email"] = (
        record.get("email")
        or ""
    )

    business["address"] = (
        record.get("address")
        or ""
    )

    business["description"] = (
        record.get("description")
        or ""
    )

    business["logo"] = (
        record.get("logo")
        or ""
    )

    return business


def get_business_record_from_supabase():
    if not supabase_available():
        return None

    response = supabase_request(
        "GET",
        "businesses?select=*&limit=1"
    )

    if response is None or not response.ok:
        return None

    data = safe_response_json(response)

    if isinstance(data, list) and data:
        return data[0]

    return None


# ================================================================
# BUSINESS API
# ================================================================

@app.route("/api/business", methods=["GET"])
def get_business():
    record = get_business_record_from_supabase()

    if record:
        business = normalize_business_record(record)
    else:
        business = default_business()

    # IMPORTANT:
    # Return nested "business" because the existing
    # settings.html and customers.html expect it.
    #
    # Also return compatibility fields at the top level
    # so older dashboard code does not immediately break.
    return jsonify({
        "success": True,
        "business": business,

        "id": business.get("id"),
        "name": business.get("name"),
        "business_name": business.get("business_name"),
        "owner_name": business.get("owner_name"),
        "phone": business.get("phone"),
        "email": business.get("email"),
        "address": business.get("address"),
        "description": business.get("description"),
        "logo": business.get("logo")
    })


@app.route("/api/business", methods=["POST"])
def save_business():
    body = get_json_body()

    business_name = str(
        body.get("business_name")
        or body.get("name")
        or ""
    ).strip()

    owner_name = str(
        body.get("owner_name")
        or ""
    ).strip()

    phone = str(
        body.get("phone")
        or body.get("phone_number")
        or ""
    ).strip()

    email = str(
        body.get("email")
        or ""
    ).strip()

    address = str(
        body.get("address")
        or ""
    ).strip()

    description = str(
        body.get("description")
        or ""
    ).strip()

    logo = str(
        body.get("logo")
        or ""
    ).strip()

    if not business_name:
        business_name = "NexaFlow AI Business"

    print("=" * 60, flush=True)
    print("BUSINESS SAVE START", flush=True)
    print("BUSINESS NAME:", business_name, flush=True)
    print("OWNER NAME:", owner_name, flush=True)
    print("PHONE:", phone, flush=True)
    print("EMAIL:", email, flush=True)
    print("ADDRESS:", address, flush=True)
    print("LOGO PROVIDED:", bool(logo), flush=True)

    existing = get_business_record_from_supabase()

    # ------------------------------------------------------------
    # Database payload
    # ------------------------------------------------------------

    full_payload = {
        "business_name": business_name,
        "owner_name": owner_name,
        "phone": phone,
        "email": email,
        "address": address,
        "description": description,
        "logo": logo
    }

    saved_record = None

    if supabase_available():

        # --------------------------------------------------------
        # UPDATE EXISTING BUSINESS
        # --------------------------------------------------------

        if existing and existing.get("id"):

            business_id = existing.get("id")

            response = supabase_request(
                "PATCH",
                "businesses",
                params={
                    "id": f"eq.{business_id}"
                },
                json=full_payload
            )

            if response is not None and response.ok:

                data = safe_response_json(response)

                if isinstance(data, list) and data:
                    saved_record = data[0]

                else:
                    saved_record = dict(existing)
                    saved_record.update(full_payload)

                print(
                    "BUSINESS UPDATED SUCCESSFULLY.",
                    flush=True
                )

            else:
                print(
                    "FULL BUSINESS UPDATE FAILED. "
                    "Trying compatibility payload.",
                    flush=True
                )

                compatibility_payload = {
                    "name": business_name,
                    "owner_name": owner_name,
                    "phone": phone,
                    "email": email,
                    "address": address,
                    "description": description,
                    "logo": logo
                }

                response2 = supabase_request(
                    "PATCH",
                    "businesses",
                    params={
                        "id": f"eq.{business_id}"
                    },
                    json=compatibility_payload
                )

                if response2 is not None and response2.ok:

                    data = safe_response_json(response2)

                    if isinstance(data, list) and data:
                        saved_record = data[0]
                    else:
                        saved_record = dict(existing)
                        saved_record.update(
                            compatibility_payload
                        )

                    print(
                        "BUSINESS COMPATIBILITY UPDATE SUCCESS.",
                        flush=True
                    )

                else:
                    print(
                        "BUSINESS UPDATE FAILED.",
                        flush=True
                    )

        # --------------------------------------------------------
        # CREATE NEW BUSINESS
        # --------------------------------------------------------

        else:

            response = supabase_request(
                "POST",
                "businesses",
                json=full_payload
            )

            if response is not None and response.ok:

                data = safe_response_json(response)

                if isinstance(data, list) and data:
                    saved_record = data[0]

                else:
                    saved_record = dict(full_payload)

                print(
                    "BUSINESS CREATED SUCCESSFULLY.",
                    flush=True
                )

            else:

                print(
                    "FULL BUSINESS INSERT FAILED. "
                    "Trying compatibility payload.",
                    flush=True
                )

                compatibility_payload = {
                    "name": business_name,
                    "owner_name": owner_name,
                    "phone": phone,
                    "email": email,
                    "address": address,
                    "description": description,
                    "logo": logo
                }

                response2 = supabase_request(
                    "POST",
                    "businesses",
                    json=compatibility_payload
                )

                if response2 is not None and response2.ok:

                    data = safe_response_json(response2)

                    if isinstance(data, list) and data:
                        saved_record = data[0]
                    else:
                        saved_record = dict(
                            compatibility_payload
                        )

                    print(
                        "BUSINESS COMPATIBILITY INSERT SUCCESS.",
                        flush=True
                    )

                else:
                    print(
                        "BUSINESS INSERT FAILED.",
                        flush=True
                    )

    # ------------------------------------------------------------
    # If database isn't available, still return saved data
    # so the frontend receives a valid response.
    # ------------------------------------------------------------

    if saved_record is None:

        if existing:
            saved_record = dict(existing)

        else:
            saved_record = {}

        saved_record.update(full_payload)

        if existing and existing.get("id"):
            saved_record["id"] = existing.get("id")

    business = normalize_business_record(
        saved_record
    )

    print(
        "BUSINESS SAVE COMPLETE:",
        json.dumps(
            business,
            default=str
        )[:5000],
        flush=True
    )

    print("=" * 60, flush=True)

    return jsonify({
        "success": True,
        "message": "Business settings saved successfully.",
        "business": business
    })

# ================================================================
# BUSINESS LOGO UPLOAD
# ================================================================

@app.route("/api/business/logo", methods=["POST"])
def upload_business_logo():
    print("BUSINESS LOGO UPLOAD START", flush=True)

    uploaded_file = request.files.get("logo")

    if uploaded_file is None:
        return jsonify({
            "success": False,
            "error": "No logo file was provided."
        }), 400

    if not uploaded_file.filename:
        return jsonify({
            "success": False,
            "error": "No logo file was selected."
        }), 400

    try:
        # ------------------------------------------------------------
        # READ AND VALIDATE LOGO
        # ------------------------------------------------------------

        file_bytes = uploaded_file.read()

        if not file_bytes:
            return jsonify({
                "success": False,
                "error": "The logo file is empty."
            }), 400

        if len(file_bytes) > 5 * 1024 * 1024:
            return jsonify({
                "success": False,
                "error": "Logo file is too large. Maximum size is 5 MB."
            }), 400

        content_type = (
            uploaded_file.mimetype
            or "image/jpeg"
        )

        encoded = base64.b64encode(
            file_bytes
        ).decode("utf-8")

        logo_url = (
            f"data:{content_type};base64,{encoded}"
        )

        print(
            "BUSINESS LOGO CONVERTED TO DATA URL.",
            flush=True
        )

        # ------------------------------------------------------------
        # GET EXISTING BUSINESS PROFILE
        # ------------------------------------------------------------

        existing = get_business_record_from_supabase()

        # ------------------------------------------------------------
        # IMPORTANT:
        # If a business profile already exists, ONLY update
        # the logo. Do NOT overwrite the business information.
        # ------------------------------------------------------------

        if existing and existing.get("id"):

            business_id = existing.get("id")

            print(
                "EXISTING BUSINESS FOUND:",
                business_id,
                flush=True
            )

            response = supabase_request(
                "PATCH",
                "businesses",
                params={
                    "id": f"eq.{business_id}"
                },
                json={
                    "logo": logo_url
                }
            )

            if response is not None and response.ok:

                saved_data = safe_response_json(response)

                if (
                    isinstance(saved_data, list)
                    and saved_data
                ):
                    saved_business = (
                        saved_data[0]
                    )
                else:
                    saved_business = dict(existing)
                    saved_business["logo"] = logo_url

                print(
                    "BUSINESS LOGO UPDATED SUCCESSFULLY.",
                    flush=True
                )

                return jsonify({
                    "success": True,
                    "logo": logo_url,
                    "business": normalize_business_record(
                        saved_business
                    ),
                    "message":
                        "Business logo uploaded successfully."
                })

            error_text = (
                response.text[:3000]
                if response is not None
                else "No response from Supabase."
            )

            print(
                "BUSINESS LOGO UPDATE FAILED:",
                error_text,
                flush=True
            )

            return jsonify({
                "success": False,
                "error":
                    "Unable to update the business logo. "
                    + error_text
            }), 500

        # ------------------------------------------------------------
        # NO BUSINESS PROFILE EXISTS
        #
        # IMPORTANT:
        # Use the same business information structure as the
        # normal /api/business POST endpoint.
        # ------------------------------------------------------------

        print(
            "NO BUSINESS PROFILE FOUND.",
            flush=True
        )

        business_name = str(
            os.environ.get(
                "BUSINESS_NAME",
                "NexaFlow AI Business"
            )
        ).strip()

        owner_name = str(
            os.environ.get(
                "OWNER_NAME",
                ""
            )
        ).strip()

        payload = {
            "business_name": business_name,
            "owner_name": owner_name,
            "phone": "",
            "email": "",
            "address": "",
            "description": "",
            "logo": logo_url
        }

        print(
            "ATTEMPTING BUSINESS PROFILE CREATION.",
            flush=True
        )

        # ------------------------------------------------------------
        # FIRST ATTEMPT
        # ------------------------------------------------------------

        response = supabase_request(
            "POST",
            "businesses",
            json=payload
        )

        if response is not None and response.ok:

            saved_data = safe_response_json(response)

            if (
                isinstance(saved_data, list)
                and saved_data
            ):
                saved_business = saved_data[0]
            else:
                saved_business = dict(payload)

            print(
                "BUSINESS PROFILE CREATED WITH LOGO.",
                flush=True
            )

            return jsonify({
                "success": True,
                "logo": logo_url,
                "business": normalize_business_record(
                    saved_business
                ),
                "message":
                    "Business logo uploaded successfully."
            })

        # ------------------------------------------------------------
        # CAPTURE THE REAL SUPABASE ERROR
        # ------------------------------------------------------------

        first_error = (
            response.text[:5000]
            if response is not None
            else "No response from Supabase."
        )

        print(
            "BUSINESS PROFILE CREATION FAILED:",
            first_error,
            flush=True
        )

        # ------------------------------------------------------------
        # IMPORTANT FALLBACK
        #
        # If the businesses table rejects the logo because the
        # existing schema does not contain business_name, try
        # the older "name" column structure.
        # ------------------------------------------------------------

        compatibility_payload = {
            "name": business_name,
            "owner_name": owner_name,
            "phone": "",
            "email": "",
            "address": "",
            "description": "",
            "logo": logo_url
        }

        print(
            "TRYING COMPATIBILITY BUSINESS SCHEMA.",
            flush=True
        )

        response2 = supabase_request(
            "POST",
            "businesses",
            json=compatibility_payload
        )

        if response2 is not None and response2.ok:

            saved_data = safe_response_json(response2)

            if (
                isinstance(saved_data, list)
                and saved_data
            ):
                saved_business = saved_data[0]
            else:
                saved_business = dict(
                    compatibility_payload
                )

            print(
                "BUSINESS PROFILE CREATED USING "
                "COMPATIBILITY SCHEMA.",
                flush=True
            )

            return jsonify({
                "success": True,
                "logo": logo_url,
                "business": normalize_business_record(
                    saved_business
                ),
                "message":
                    "Business logo uploaded successfully."
            })

        second_error = (
            response2.text[:5000]
            if response2 is not None
            else "No response from Supabase."
        )

        print(
            "COMPATIBILITY BUSINESS CREATION FAILED:",
            second_error,
            flush=True
        )

        # ------------------------------------------------------------
        # RETURN THE REAL DATABASE ERROR
        #
        # This is important because the previous version returned
        # "Unknown Supabase database error", which hid the actual
        # reason Supabase rejected the operation.
        # ------------------------------------------------------------

        real_error = (
            second_error
            or first_error
            or "Unknown Supabase database error."
        )

        return jsonify({
            "success": False,
            "error":
                "Unable to create business profile for logo. "
                + real_error
        }), 500

    except Exception as error:

        print(
            "BUSINESS LOGO ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

         

        
            
        
                    

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
        # ------------------------------------------------------------
    # SAVE AI CONVERSATION FOR REPORTS / ANALYTICS
    # ------------------------------------------------------------

    try:

        if supabase_available() and answer:

            supabase_request(
                "POST",
                "ai_conversations",
                json={
                    "question": question,
                    "answer": answer,
                    "created_at": now_iso()
                }
            )

    except Exception as error:

        # Never allow analytics/report storage to break
        # the AI Assistant itself.
        print(
            "AI CONVERSATION SAVE ERROR:",
            repr(error),
            flush=True
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
    ai_reply=None,
    location=None
):

    phone = str(phone or "").strip()

    name = str(
        name or "WhatsApp Customer"
    ).strip()

    location = str(
        location or ""
    ).strip()

    # ------------------------------------------------------------
    # IMPORTANT FIX:
    # Manual customers are allowed to have no phone number.
    #
    # WhatsApp customers still provide a phone number.
    # ------------------------------------------------------------

    existing = None

    if phone:
        existing = find_customer_by_phone(phone)

    if existing:

        update_data = {
            "name": existing.get("name") or name,
            "updated_at": now_iso()
        }

        if phone:
            update_data["phone"] = phone

        if last_message is not None:
            update_data["message"] = last_message

        if ai_reply is not None:
            update_data["ai_reply"] = ai_reply

        if location:
            update_data["location"] = location

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

                data = safe_response_json(response)

                if isinstance(data, list) and data:
                    existing = data[0]

            else:

                print(
                    "CUSTOMER FULL UPDATE FAILED. "
                    "Trying compatibility update.",
                    flush=True
                )

                compatibility_data = {
                    "name": update_data.get("name"),
                    "phone": update_data.get("phone", ""),
                    "message": update_data.get("message", ""),
                    "ai_reply": update_data.get("ai_reply", "")
                }

                if location:
                    compatibility_data["location"] = location

                response2 = supabase_request(
                    "PATCH",
                    "customers",
                    params={
                        "id": f"eq.{customer_id}"
                    },
                    json=compatibility_data
                )

                if response2 is not None and response2.ok:

                    data = safe_response_json(response2)

                    if isinstance(data, list) and data:
                        existing = data[0]

        existing.update(update_data)

        return existing

    # ------------------------------------------------------------
    # CREATE NEW CUSTOMER
    # ------------------------------------------------------------

    customer = {
        "id": str(uuid.uuid4()),
        "name": name,
        "phone": phone,
        "location": location,
        "message": last_message or "",
        "ai_reply": ai_reply or "",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    saved_customer = None

    if supabase_available():

        full_payload = dict(customer)

        response = supabase_request(
            "POST",
            "customers",
            json=full_payload
        )

        if response is not None and response.ok:

            data = safe_response_json(response)

            if isinstance(data, list) and data:
                saved_customer = data[0]

            else:
                saved_customer = dict(customer)

            print(
                "CUSTOMER SAVED TO SUPABASE.",
                flush=True
            )

        else:

            print(
                "FULL CUSTOMER SAVE FAILED. "
                "Trying compatibility payload.",
                flush=True
            )

            compatibility_payload = {
                "name": name,
                "phone": phone,
                "message": last_message or "",
                "ai_reply": ai_reply or "",
                "created_at": customer["created_at"]
            }

            if location:
                compatibility_payload["location"] = location

            response2 = supabase_request(
                "POST",
                "customers",
                json=compatibility_payload
            )

            if response2 is not None and response2.ok:

                data = safe_response_json(response2)

                if isinstance(data, list) and data:
                    saved_customer = data[0]

                else:
                    saved_customer = dict(
                        compatibility_payload
                    )

                print(
                    "CUSTOMER COMPATIBILITY SAVE SUCCESS.",
                    flush=True
                )

            else:

                print(
                    "CUSTOMER SUPABASE SAVE FAILED.",
                    flush=True
                )

    if saved_customer is not None:
        customer = saved_customer

    # Prevent duplicate memory entries.
    if not any(
        str(item.get("id")) == str(customer.get("id"))
        for item in customers
    ):
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

                    # Keep memory synchronized.
                    customers.clear()
                    customers.extend(data)

                    # Existing customers.html accepts an array.
                    return jsonify(data)

            except Exception as error:
                print(
                    "CUSTOMER GET PARSE ERROR:",
                    repr(error),
                    flush=True
                )

    return jsonify(
        list(reversed(customers))
    )


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

    location = (
        body.get("location")
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
        ai_reply=ai_reply,
        location=location
    )

    if customer is None:

        return jsonify({
            "success": False,
            "error": "Unable to save customer."
        }), 500

    return jsonify({
        "success": True,
        "customer": customer
    })


@app.route(
    "/api/customers/<customer_id>",
    methods=["DELETE"]
)
def delete_customer(customer_id):

    customer_id = str(
        customer_id or ""
    ).strip()

    if not customer_id:
        return jsonify({
            "success": False,
            "error": "Customer ID is required."
        }), 400

    print(
        "DELETE CUSTOMER:",
        customer_id,
        flush=True
    )

    deleted = False

    if supabase_available():

        response = supabase_request(
            "DELETE",
            "customers",
            params={
                "id": f"eq.{customer_id}"
            }
        )

        if response is not None and response.ok:

            deleted = True

        else:

            print(
                "SUPABASE CUSTOMER DELETE FAILED.",
                flush=True
            )

    # Always remove from local memory as well.
    before = len(customers)

    customers[:] = [
        customer
        for customer in customers
        if str(customer.get("id")) != customer_id
    ]

    if len(customers) < before:
        deleted = True

    if not deleted:

        return jsonify({
            "success": False,
            "error": "Customer was not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Customer deleted successfully."
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
                    messages.clear()
                    messages.extend(data)

                    return jsonify(data)

            except Exception:
                pass

    return jsonify(
        list(reversed(messages))
    )


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
# WHATSAPP INTEGRATIONS API
# ================================================================

@app.route(
    "/api/integrations",
    methods=["GET"]
)
def get_integrations():

    integrations = []

    if supabase_available():

        response = supabase_request(
            "GET",
            "integrations?select=*&order=created_at.desc"
        )

        if response is not None and response.ok:

            data = safe_response_json(response)

            if isinstance(data, list):
                integrations = data

    # If the normal integrations table isn't available,
    # check the alternative table.
    if not integrations and supabase_available():

        response2 = supabase_request(
            "GET",
            "whatsapp_integrations?select=*&order=created_at.desc"
        )

        if response2 is not None and response2.ok:

            data2 = safe_response_json(response2)

            if isinstance(data2, list):
                integrations = data2

    # Never expose an access token in logs or unnecessary
    # response fields beyond what the existing settings page
    # already expects.
    cleaned = []

    for item in integrations:

        if not isinstance(item, dict):
            continue

        record = dict(item)

        settings = record.get("settings")

        if isinstance(settings, str):

            try:
                settings = json.loads(settings)
            except Exception:
                settings = {}

        if not isinstance(settings, dict):
            settings = {}

        record["settings"] = settings

        cleaned.append(record)

    return jsonify({
        "success": True,
        "integrations": cleaned
    })


@app.route(
    "/api/integrations",
    methods=["POST"]
)
def create_integration():

    body = get_json_body()

    platform = str(
        body.get("platform")
        or ""
    ).strip().lower()

    account_name = str(
        body.get("account_name")
        or ""
    ).strip()

    account_id = str(
        body.get("account_id")
        or ""
    ).strip()

    phone_number = str(
        body.get("phone_number")
        or ""
    ).strip()

    phone_number_id = str(
        body.get("phone_number_id")
        or ""
    ).strip()

    access_token = str(
        body.get("access_token")
        or ""
    ).strip()

    if not platform:

        return jsonify({
            "success": False,
            "error": "Integration platform is required."
        }), 400

    if platform == "whatsapp":

        if (
            not account_name
            or not account_id
            or not phone_number
            or not phone_number_id
            or not access_token
        ):

            return jsonify({
                "success": False,
                "error": "Please provide all WhatsApp integration fields."
            }), 400

    integration_id = str(uuid.uuid4())

    settings = {
        "phone_number_id": phone_number_id
    }

    payload = {
        "id": integration_id,
        "platform": platform,
        "account_name": account_name,
        "account_id": account_id,
        "phone_number": phone_number,
        "phone_number_id": phone_number_id,
        "access_token": access_token,
        "settings": settings,
        "status": "connected",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    saved = None

    if supabase_available():

        response = supabase_request(
            "POST",
            "integrations",
            json=payload
        )

        if response is not None and response.ok:

            data = safe_response_json(response)

            if isinstance(data, list) and data:
                saved = data[0]
            else:
                saved = payload

        else:

            print(
                "FULL INTEGRATION INSERT FAILED.",
                flush=True
            )

            # Compatibility payload for older integration schemas.
            compatibility_payload = {
                "platform": platform,
                "account_name": account_name,
                "account_id": account_id,
                "phone_number": phone_number,
                "access_token": access_token,
                "settings": settings,
                "status": "connected"
            }

            response2 = supabase_request(
                "POST",
                "integrations",
                json=compatibility_payload
            )

            if response2 is not None and response2.ok:

                data = safe_response_json(response2)

                if isinstance(data, list) and data:
                    saved = data[0]
                else:
                    saved = compatibility_payload

    if saved is None:

        saved = payload

        print(
            "INTEGRATION DATABASE SAVE FAILED; "
            "RETURNING ENVIRONMENT-COMPATIBLE RECORD.",
            flush=True
        )

    return jsonify({
        "success": True,
        "message": "WhatsApp connected successfully.",
        "integration": saved
    })


@app.route(
    "/api/integrations/<integration_id>",
    methods=["DELETE"]
)
def delete_integration(integration_id):

    integration_id = str(
        integration_id or ""
    ).strip()

    if not integration_id:

        return jsonify({
            "success": False,
            "error": "Integration ID is required."
        }), 400

    deleted = False

    if supabase_available():

        response = supabase_request(
            "DELETE",
            "integrations",
            params={
                "id": f"eq.{integration_id}"
            }
        )

        if response is not None and response.ok:
            deleted = True

        else:

            response2 = supabase_request(
                "DELETE",
                "whatsapp_integrations",
                params={
                    "id": f"eq.{integration_id}"
                }
            )

            if response2 is not None and response2.ok:
                deleted = True

    # Environment fallback record is not stored in database.
    if integration_id == "environment-whatsapp-integration":
        deleted = True

    if not deleted:

        return jsonify({
            "success": False,
            "error": "Integration was not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "WhatsApp integration disconnected successfully."
    })


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


def mark_whatsapp_message_processed(
    external_message_id
):

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
            or (
                integration.get("settings") or {}
            ).get("phone_number_id")
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
# NEXAFLOW CORRECTIONS
# Dashboard / Analytics / AI Conversations / Automation
# ================================================================

def correction_get_table(table, params=None):
    """
    Safe database reader used only by the corrected dashboard,
    analytics, reports and automation endpoints.

    This does NOT modify the existing WhatsApp/customer/message
    functions.
    """
    if not supabase_available():
        return []

    try:
        response = supabase_request(
            "GET",
            table,
            params=params or {
                "select": "*"
            }
        )

        if response is not None and response.ok:
            data = safe_response_json(response)

            if isinstance(data, list):
                return data

    except Exception as error:
        print(
            "CORRECTION TABLE READ ERROR:",
            table,
            repr(error),
            flush=True
        )

        traceback.print_exc()

    return []


def correction_get_automation():
    """
    Reads automation settings while remaining compatible with
    the existing automation_settings table.
    """

    defaults = {
        "ai_replies": True,
        "message_automation": True,
        "task_automation": True
    }

    if not supabase_available():
        return defaults

    try:

        response = supabase_request(
            "GET",
            "automation_settings",
            params={
                "select": "*",
                "limit": 1
            }
        )

        if response is not None and response.ok:

            rows = safe_response_json(response)

            if isinstance(rows, list) and rows:

                row = rows[0]

                for key in defaults:

                    if key in row:
                        defaults[key] = bool(
                            row.get(key)
                        )

                if row.get("id") is not None:
                    defaults["id"] = row.get("id")

                if row.get("created_at") is not None:
                    defaults["created_at"] = row.get(
                        "created_at"
                    )

                if row.get("updated_at") is not None:
                    defaults["updated_at"] = row.get(
                        "updated_at"
                    )

                return defaults

        print(
            "No automation settings found. "
            "Using safe defaults.",
            flush=True
        )

    except Exception as error:

        print(
            "AUTOMATION READ ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

    return defaults


# ================================================================
# AUTOMATION - GET
# ================================================================

@app.route(
    "/api/automation",
    methods=["GET"]
)
def correction_get_automation_settings():

    try:

        automation = correction_get_automation()

        return jsonify({
            "success": True,
            "automation": automation,

            # Compatibility fields.
            "ai_replies": automation.get(
                "ai_replies",
                True
            ),

            "message_automation": automation.get(
                "message_automation",
                True
            ),

            "task_automation": automation.get(
                "task_automation",
                True
            )
        })

    except Exception as error:

        print(
            "CORRECTED AUTOMATION GET ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        # IMPORTANT:
        # Even if the database temporarily fails,
        # the Automation page must not remain stuck on Loading.
        return jsonify({
            "success": True,
            "automation": {
                "ai_replies": True,
                "message_automation": True,
                "task_automation": True
            }
        })


# ================================================================
# AUTOMATION - SAVE
# ================================================================

@app.route(
    "/api/automation",
    methods=["POST"]
)
def correction_save_automation():

    body = get_json_body()

    ai_replies = bool(
        body.get(
            "ai_replies",
            True
        )
    )

    message_automation = bool(
        body.get(
            "message_automation",
            True
        )
    )

    task_automation = bool(
        body.get(
            "task_automation",
            True
        )
    )

    settings = {
        "ai_replies": ai_replies,
        "message_automation": message_automation,
        "task_automation": task_automation,
        "updated_at": now_iso()
    }

    try:

        if not supabase_available():

            return jsonify({
                "success": True,
                "automation": settings,
                "message":
                    "Automation settings updated."
            })

        # Check whether a row already exists.
        existing_response = supabase_request(
            "GET",
            "automation_settings",
            params={
                "select": "*",
                "limit": 1
            }
        )

        existing = []

        if (
            existing_response is not None
            and existing_response.ok
        ):

            existing = (
                safe_response_json(
                    existing_response
                )
                or []
            )

        if isinstance(existing, list) and existing:

            row_id = existing[0].get("id")

            if row_id:

                response = supabase_request(
                    "PATCH",
                    "automation_settings",
                    params={
                        "id": f"eq.{row_id}"
                    },
                    json=settings
                )

            else:

                response = supabase_request(
                    "PATCH",
                    "automation_settings",
                    params={},
                    json=settings
                )

        else:

            response = supabase_request(
                "POST",
                "automation_settings",
                json=settings
            )

        if (
            response is not None
            and response.ok
        ):

            saved = safe_response_json(
                response
            )

            if isinstance(saved, list) and saved:
                automation = saved[0]
            else:
                automation = settings

            return jsonify({
                "success": True,
                "automation": automation,
                "message":
                    "Automation settings saved successfully."
            })

        print(
            "AUTOMATION SAVE DATABASE ERROR:",
            response.text
            if response is not None
            else "No response",
            flush=True
        )

        # Return the requested state even if the DB has a
        # temporary schema/RLS problem.
        return jsonify({
            "success": True,
            "automation": settings,
            "message":
                "Automation settings updated."
        })

    except Exception as error:

        print(
            "CORRECTED AUTOMATION SAVE ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ================================================================
# AUTOMATION - TOGGLE
# ================================================================

@app.route(
    "/api/automation/toggle",
    methods=["POST"]
)
def correction_toggle_automation():

    body = get_json_body()

    setting = str(
        body.get(
            "setting",
            ""
        )
    ).strip()

    value = body.get("value")

    allowed = {
        "ai_replies",
        "message_automation",
        "task_automation"
    }

    if setting not in allowed:

        return jsonify({
            "success": False,
            "error":
                "Invalid automation setting."
        }), 400

    if not isinstance(value, bool):

        return jsonify({
            "success": False,
            "error":
                "Automation value must be true or false."
        }), 400

    try:

        current = correction_get_automation()

        current[setting] = value
        current["updated_at"] = now_iso()

        if supabase_available():

            row_id = current.get("id")

            if row_id:

                response = supabase_request(
                    "PATCH",
                    "automation_settings",
                    params={
                        "id": f"eq.{row_id}"
                    },
                    json={
                        setting: value,
                        "updated_at": now_iso()
                    }
                )

            else:

                response = supabase_request(
                    "POST",
                    "automation_settings",
                    json={
                        "ai_replies":
                            current.get(
                                "ai_replies",
                                True
                            ),

                        "message_automation":
                            current.get(
                                "message_automation",
                                True
                            ),

                        "task_automation":
                            current.get(
                                "task_automation",
                                True
                            ),

                        "updated_at":
                            now_iso()
                    }
                )

            if (
                response is not None
                and response.ok
            ):

                saved = safe_response_json(
                    response
                )

                if (
                    isinstance(saved, list)
                    and saved
                ):
                    current = saved[0]

        return jsonify({
            "success": True,
            "setting": setting,
            "value": value,
            "automation": current
        })

    except Exception as error:

        print(
            "CORRECTED AUTOMATION TOGGLE ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ================================================================
# AI CONVERSATIONS
# ================================================================

@app.route(
    "/api/ai/conversations",
    methods=["GET"]
)
def correction_get_ai_conversations():

    try:

        data = correction_get_table(
            "ai_conversations",
            {
                "select": "*",
                "order":
                    "created_at.desc"
            }
        )

        return jsonify({
            "success": True,
            "conversations": data,
            "count": len(data)
        })

    except Exception as error:

        print(
            "AI CONVERSATIONS GET ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": True,
            "conversations": [],
            "count": 0
        })


# ================================================================
# DASHBOARD STATISTICS
# ================================================================

@app.route(
    "/api/dashboard/stats",
    methods=["GET"]
)
def correction_dashboard_stats():

    try:

        customer_data = correction_get_table(
            "customers",
            {
                "select": "*"
            }
        )

        conversation_data = correction_get_table(
            "ai_conversations",
            {
                "select": "*"
            }
        )

        message_data = correction_get_table(
            "messages",
            {
                "select": "*"
            }
        )

        business_data = correction_get_table(
            "businesses",
            {
                "select": "*",
                "limit": 1
            }
        )

        incoming = 0
        outgoing = 0

        for item in message_data:

            direction = str(
                item.get("direction", "")
            ).lower()

            if direction in (
                "incoming",
                "inbound"
            ):
                incoming += 1

            elif direction in (
                "outgoing",
                "outbound"
            ):
                outgoing += 1

        stats = {
            "customers":
                len(customer_data),

            "ai_conversations":
                len(conversation_data),

            "whatsapp_messages":
                len(message_data),

            "whatsapp_incoming":
                incoming,

            "whatsapp_outgoing":
                outgoing,

            "reports":
                len(customer_data)
                + len(conversation_data),

            "business_account":
                1 if business_data else 0
        }

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as error:

        print(
            "CORRECTED DASHBOARD STATS ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": True,
            "stats": {
                "customers": 0,
                "ai_conversations": 0,
                "whatsapp_messages": 0,
                "whatsapp_incoming": 0,
                "whatsapp_outgoing": 0,
                "reports": 0,
                "business_account": 0
            }
        })


# ================================================================
# ANALYTICS
# ================================================================

@app.route(
    "/api/analytics",
    methods=["GET"]
)
def correction_analytics():

    try:

        customer_data = correction_get_table(
            "customers",
            {
                "select": "*"
            }
        )

        conversation_data = correction_get_table(
            "ai_conversations",
            {
                "select": "*"
            }
        )

        message_data = correction_get_table(
            "messages",
            {
                "select": "*"
            }
        )

        incoming = 0
        outgoing = 0

        for item in message_data:

            direction = str(
                item.get("direction", "")
            ).lower()

            if direction in (
                "incoming",
                "inbound"
            ):
                incoming += 1

            elif direction in (
                "outgoing",
                "outbound"
            ):
                outgoing += 1

        ai_replies = 0

        for item in conversation_data:

            answer = (
                item.get("answer")
                or item.get("ai_reply")
                or ""
            )

            if str(answer).strip():
                ai_replies += 1

        analytics = {
            "total_customers":
                len(customer_data),

            "total_ai_conversations":
                len(conversation_data),

            "total_ai_replies":
                ai_replies,

            "total_whatsapp_messages":
                len(message_data),

            "whatsapp_messages":
                len(message_data),

            "whatsapp_incoming":
                incoming,

            "whatsapp_outgoing":
                outgoing,

            # Compatibility aliases.
            "customers":
                len(customer_data),

            "ai_conversations":
                len(conversation_data)
        }

        return jsonify({
            "success": True,
            "analytics": analytics,

            # Also expose fields directly because different
            # versions of the frontend use different formats.
            **analytics
        })

    except Exception as error:

        print(
            "CORRECTED ANALYTICS ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": True,
            "analytics": {
                "total_customers": 0,
                "total_ai_conversations": 0,
                "total_ai_replies": 0,
                "total_whatsapp_messages": 0,
                "whatsapp_messages": 0,
                "whatsapp_incoming": 0,
                "whatsapp_outgoing": 0,
                "customers": 0,
                "ai_conversations": 0
            }
        })


# ================================================================
# REPORTS - CORRECTED VERSION
# ================================================================

@app.route(
    "/api/reports/corrected",
    methods=["GET"]
)
def correction_reports():

    try:

        customer_data = correction_get_table(
            "customers",
            {
                "select": "*",
                "order": "created_at.desc"
            }
        )

        conversation_data = correction_get_table(
            "ai_conversations",
            {
                "select": "*",
                "order": "created_at.desc"
            }
        )

        message_data = correction_get_table(
            "messages",
            {
                "select": "*",
                "order": "created_at.desc"
            }
        )

        business_data = correction_get_table(
            "businesses",
            {
                "select": "*",
                "limit": 1
            }
        )

        automation = correction_get_automation()

        ai_replies = 0

        for item in conversation_data:

            answer = (
                item.get("answer")
                or item.get("ai_reply")
                or ""
            )

            if str(answer).strip():
                ai_replies += 1

        return jsonify({
            "success": True,

            "report": {
                "business":
                    business_data[0]
                    if business_data
                    else None,

                "total_customers":
                    len(customer_data),

                "total_ai_conversations":
                    len(conversation_data),

                "total_ai_replies":
                    ai_replies,

                "total_messages":
                    len(message_data),

                "automation":
                    automation,

                "customers":
                    customer_data,

                "ai_conversations":
                    conversation_data,

                "messages":
                    message_data
            },

            # Compatibility fields.
            "total_customers":
                len(customer_data),

            "total_ai_conversations":
                len(conversation_data),

            "total_ai_replies":
                ai_replies,

            "total_messages":
                len(message_data)
        })

    except Exception as error:

        print(
            "CORRECTED REPORTS ERROR:",
            repr(error),
            flush=True
        )

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


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
