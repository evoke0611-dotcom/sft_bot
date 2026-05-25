# import os
# import traceback
# import requests
# from dotenv import load_dotenv
# from fastapi import FastAPI, Request, HTTPException, Query
# from fastapi.responses import PlainTextResponse

# from src.retriever import retrieve, generate_openai_answer


# load_dotenv()

# app = FastAPI(
#     title="SFT WhatsApp RAG Chatbot",
#     description="WhatsApp chatbot backend with RAG and OpenAI answer generation.",
#     version="1.0.0"
# )


# WHATSAPP_VERIFY_TOKEN = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "").strip()
# WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
# WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
# META_API_VERSION = os.getenv("META_API_VERSION", "v21.0")


# # Temporary memory while server is running.
# # Later this can be moved to PostgreSQL or Redis.
# user_followups = {}
# processed_message_ids = set()


# @app.get("/")
# def home():
#     return {
#         "status": "running",
#         "message": "SFT WhatsApp RAG chatbot is active"
#     }


# @app.get("/health", tags=["Testing"])
# def health_check():
#     """
#     Quick environment check.
#     This does not expose secret values.
#     """

#     return {
#         "status": "ok",
#         "whatsapp_verify_token_loaded": bool(WHATSAPP_VERIFY_TOKEN),
#         "whatsapp_access_token_loaded": bool(WHATSAPP_ACCESS_TOKEN),
#         "whatsapp_phone_number_id_loaded": bool(WHATSAPP_PHONE_NUMBER_ID),
#         "meta_api_version": META_API_VERSION
#     }


# @app.get("/debug-token", tags=["Testing"])
# def debug_token():
#     return {
#         "token_loaded": bool(WHATSAPP_VERIFY_TOKEN),
#         "token_length": len(WHATSAPP_VERIFY_TOKEN),
#         "expected_length_for_sft_verify": 11
#     }


# @app.get("/query", tags=["Testing"])
# def query_endpoint(
#     q: str = Query(..., description="Type your question here")
# ):
#     """
#     Test the RAG pipeline directly from Swagger UI.
#     No WhatsApp is required for this endpoint.
#     """

#     try:
#         results = retrieve(q, top_k=5)

#         if not results:
#             answer = "Our call adviser will connect with you shortly."
#         else:
#             answer = generate_openai_answer(q, results)

#         sources = [
#             {
#                 "source": r["metadata"].get("source_file"),
#                 "page": r["metadata"].get("page"),
#                 "chunk": r["metadata"].get("chunk_index"),
#                 "similarity": round(r["similarity"], 4),
#             }
#             for r in results
#         ]

#         return {
#             "question": q,
#             "answer": answer,
#             "sources": sources,
#         }

#     except Exception as e:
#         print("Query endpoint error:")
#         print(traceback.format_exc())

#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )


# @app.get("/webhook")
# async def verify_webhook(
#     hub_mode: str = Query(None, alias="hub.mode"),
#     hub_verify_token: str = Query(None, alias="hub.verify_token"),
#     hub_challenge: str = Query(None, alias="hub.challenge")
# ):
#     """
#     Meta webhook verification endpoint.
#     """

#     if not hub_mode or not hub_verify_token or not hub_challenge:
#         raise HTTPException(
#             status_code=400,
#             detail="Missing hub.mode, hub.verify_token, or hub.challenge"
#         )

#     if hub_mode == "subscribe" and hub_verify_token.strip() == WHATSAPP_VERIFY_TOKEN:
#         return PlainTextResponse(content=hub_challenge, status_code=200)

#     raise HTTPException(
#         status_code=403,
#         detail={
#             "message": "Webhook verification failed",
#             "mode_received": hub_mode,
#             "token_received_length": len(hub_verify_token.strip()),
#             "env_token_loaded": bool(WHATSAPP_VERIFY_TOKEN),
#             "env_token_length": len(WHATSAPP_VERIFY_TOKEN)
#         }
#     )


# @app.post("/webhook")
# async def receive_whatsapp_message(request: Request):
#     """
#     Receives WhatsApp messages, sends them to the RAG pipeline,
#     generates an answer, and replies back through WhatsApp Cloud API.
#     """

#     try:
#         data = await request.json()
#         message_data = extract_message_data(data)

#         if not message_data:
#             return {"status": "no user message found"}

#         message_id = message_data["message_id"]
#         sender_number = message_data["sender_number"]
#         user_message = message_data["user_message"]

#         # Avoid duplicate replies if Meta sends the same webhook again.
#         if message_id in processed_message_ids:
#             return {"status": "duplicate message ignored"}

#         processed_message_ids.add(message_id)

#         if not user_message:
#             send_whatsapp_message(
#                 sender_number,
#                 "Please type your question clearly."
#             )
#             return {"status": "empty message handled"}

#         user_question = user_message

#         # If user replies yes, use the previous saved follow-up question.
#         if is_yes_response(user_message) and sender_number in user_followups:
#             user_question = user_followups[sender_number]
#             del user_followups[sender_number]

#         print(f"User number: {sender_number}")
#         print(f"User question: {user_question}")

#         results = retrieve(user_question, top_k=5)

#         if not results:
#             answer = "Our call adviser will connect with you shortly."
#         else:
#             answer = generate_openai_answer(user_question, results)

#         next_question = extract_next_question(answer)

#         if next_question:
#             user_followups[sender_number] = next_question

#         # WhatsApp text message limit safety.
#         answer = answer[:3500]

#         send_whatsapp_message(sender_number, answer)

#         return {"status": "message processed"}

#     except Exception as e:
#         print("Webhook error:")
#         print(traceback.format_exc())

#         return {
#             "status": "error",
#             "detail": str(e)
#         }


# def extract_message_data(data: dict):
#     """
#     Extracts useful data from WhatsApp webhook payload.
#     Handles normal text messages only.
#     """

#     try:
#         entry = data.get("entry", [])[0]
#         change = entry.get("changes", [])[0]
#         value = change.get("value", {})

#         messages = value.get("messages", [])

#         if not messages:
#             return None

#         message = messages[0]

#         message_id = message.get("id")
#         sender_number = message.get("from")
#         message_type = message.get("type")

#         if message_type == "text":
#             user_message = message.get("text", {}).get("body", "").strip()
#         else:
#             user_message = ""

#         return {
#             "message_id": message_id,
#             "sender_number": sender_number,
#             "user_message": user_message
#         }

#     except Exception:
#         return None


# def send_whatsapp_message(to_number: str, message: str):
#     """
#     Sends a text message to a WhatsApp user using Meta Cloud API.
#     """

#     if not WHATSAPP_ACCESS_TOKEN:
#         raise ValueError("WHATSAPP_ACCESS_TOKEN is missing in .env or Vercel environment variables.")

#     if not WHATSAPP_PHONE_NUMBER_ID:
#         raise ValueError("WHATSAPP_PHONE_NUMBER_ID is missing in .env or Vercel environment variables.")

#     url = (
#         f"https://graph.facebook.com/{META_API_VERSION}/"
#         f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
#     )

#     headers = {
#         "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "messaging_product": "whatsapp",
#         "to": to_number,
#         "type": "text",
#         "text": {
#             "preview_url": False,
#             "body": message
#         }
#     }

#     response = requests.post(url, headers=headers, json=payload, timeout=20)

#     if response.status_code not in [200, 201]:
#         print("WhatsApp API error:")
#         print("Status code:", response.status_code)
#         print("Response:", response.text)

#         raise ValueError(f"WhatsApp API failed with status {response.status_code}: {response.text}")

#     return response.json()


# def is_yes_response(message: str) -> bool:
#     """
#     Checks whether the user replied yes.
#     """

#     yes_words = [
#         "yes",
#         "y",
#         "yeah",
#         "yep",
#         "ok",
#         "okay",
#         "sure",
#         "yes please",
#         "haan",
#         "ha",
#         "hanji",
#         "ji",
#         "please"
#     ]

#     return message.lower().strip() in yes_words


# def extract_next_question(answer: str):
#     """
#     Extracts the follow-up question from the generated answer.
#     """

#     markers = [
#         "Next step:",
#         "Follow-up question:",
#         "Need more details?",
#         "Want to know more?",
#         "Shall I explain further?"
#     ]

#     for marker in markers:
#         if marker in answer:
#             question = answer.split(marker, 1)[1].strip()
#             return question if question else None

#     return None


import os
import traceback
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

from src.retriever import retrieve, generate_openai_answer


load_dotenv()

app = FastAPI(
    title="SFT WhatsApp RAG Chatbot",
    description="WhatsApp chatbot backend with RAG and OpenAI answer generation.",
    version="1.0.0"
)


WHATSAPP_VERIFY_TOKEN = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "").strip()
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
META_API_VERSION = os.getenv("META_API_VERSION", "v21.0")


# Temporary in-memory state. Move to Redis/PostgreSQL for production.
user_followups: dict = {}
processed_message_ids: set = set()


@app.get("/")
def home():
    return {
        "status": "running",
        "message": "SFT WhatsApp RAG chatbot is active"
    }


@app.get("/health", tags=["Testing"])
def health_check():
    """Quick environment check. Does not expose secret values."""
    return {
        "status": "ok",
        "whatsapp_verify_token_loaded": bool(WHATSAPP_VERIFY_TOKEN),
        "whatsapp_access_token_loaded": bool(WHATSAPP_ACCESS_TOKEN),
        "whatsapp_phone_number_id_loaded": bool(WHATSAPP_PHONE_NUMBER_ID),
        "meta_api_version": META_API_VERSION
    }


@app.get("/debug-token", tags=["Testing"])
def debug_token():
    return {
        "token_loaded": bool(WHATSAPP_VERIFY_TOKEN),
        "token_length": len(WHATSAPP_VERIFY_TOKEN),
    }


@app.get("/query", tags=["Testing"])
def query_endpoint(q: str = Query(..., description="Type your question here")):
    """Test the RAG pipeline directly from Swagger UI. No WhatsApp required."""
    try:
        results = retrieve(q, top_k=5)

        if not results:
            answer = "Our call adviser will connect with you shortly."
        else:
            answer = generate_openai_answer(q, results)

        sources = [
            {
                "source": r["metadata"].get("source_file"),
                "page": r["metadata"].get("page"),
                "chunk": r["metadata"].get("chunk_index"),
                "similarity": round(r["similarity"], 4),
            }
            for r in results
        ]

        return {"question": q, "answer": answer, "sources": sources}

    except Exception as e:
        print("Query endpoint error:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """Meta webhook verification endpoint."""
    if not hub_mode or not hub_verify_token or not hub_challenge:
        raise HTTPException(
            status_code=400,
            detail="Missing hub.mode, hub.verify_token, or hub.challenge"
        )

    if hub_mode == "subscribe" and hub_verify_token.strip() == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge, status_code=200)

    raise HTTPException(
        status_code=403,
        detail={
            "message": "Webhook verification failed",
            "mode_received": hub_mode,
            "token_received_length": len(hub_verify_token.strip()),
            "env_token_loaded": bool(WHATSAPP_VERIFY_TOKEN),
            "env_token_length": len(WHATSAPP_VERIFY_TOKEN)
        }
    )


@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """
    Receives WhatsApp messages, runs the RAG pipeline,
    and replies through WhatsApp Cloud API.

    Always returns HTTP 200 so Meta does not retry the webhook.
    """
    try:
        data = await request.json()

        # ── FIX 1: Log the raw payload so you can see exactly what Meta sends ──
        print("=== Incoming webhook payload ===")
        import json
        print(json.dumps(data, indent=2))
        print("================================")

        # ── FIX 2: Ignore status update events (read receipts, delivery reports) ──
        # These also POST to /webhook but contain no "messages" key.
        # Without this guard the bot used to crash silently or process garbage.
        entry = data.get("entry", [])
        if entry:
            value = entry[0].get("changes", [{}])[0].get("value", {})
            if "statuses" in value and "messages" not in value:
                print("Received a status update event — ignoring.")
                return {"status": "status update ignored"}

        message_data = extract_message_data(data)

        if not message_data:
            print("No user message found in payload.")
            return {"status": "no user message found"}

        message_id    = message_data["message_id"]
        sender_number = message_data["sender_number"]
        user_message  = message_data["user_message"]

        # ── FIX 3: Deduplicate — Meta sometimes sends the same webhook twice ──
        if message_id in processed_message_ids:
            print(f"Duplicate message {message_id} — ignoring.")
            return {"status": "duplicate message ignored"}

        processed_message_ids.add(message_id)

        # ── FIX 4: Mark the message as read so the double-tick turns blue ──
        # This also stops Meta from resending the webhook.
        mark_message_as_read(message_id)

        print(f"Sender : {sender_number}")
        print(f"Message: {user_message!r}")

        if not user_message:
            send_whatsapp_message(sender_number, "Please type your question clearly.")
            return {"status": "empty message handled"}

        # If the user replied "yes/ok/haan", expand using the stored follow-up.
        user_question = user_message
        if is_yes_response(user_message) and sender_number in user_followups:
            user_question = user_followups.pop(sender_number)
            print(f"Expanded follow-up question: {user_question!r}")

        # ── RAG pipeline ──
        results = retrieve(user_question, top_k=5)
        print(f"Retrieved {len(results)} chunks from pgvector.")

        if not results:
            answer = "Our call adviser will connect with you shortly."
        else:
            answer = generate_openai_answer(user_question, results)

        print(f"Generated answer ({len(answer)} chars)")

        # Store follow-up question for the next turn if the LLM included one.
        next_question = extract_next_question(answer)
        if next_question:
            user_followups[sender_number] = next_question
            print(f"Stored follow-up: {next_question!r}")

        # WhatsApp hard limit is 4096 chars; we stay safely under it.
        send_whatsapp_message(sender_number, answer[:3500])

        return {"status": "message processed"}

    except Exception:
        # ── FIX 5: Always return 200 so Meta does not retry endlessly ──
        # Log the full traceback so you can debug from your server logs.
        print("=== Webhook exception ===")
        print(traceback.format_exc())
        print("=========================")
        return {"status": "error — check server logs"}


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

def extract_message_data(data: dict):
    """
    Pulls the sender number, message ID, and text body out of a
    WhatsApp Cloud API webhook payload.
    Returns None if the payload has no text message.
    """
    try:
        entry  = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value  = change.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return None

        message      = messages[0]
        message_id   = message.get("id")
        sender_number = message.get("from")
        message_type = message.get("type")

        if message_type == "text":
            user_message = message.get("text", {}).get("body", "").strip()
        else:
            # Non-text types (image, audio, sticker …) — not handled yet.
            print(f"Unsupported message type received: {message_type!r}")
            user_message = ""

        return {
            "message_id":    message_id,
            "sender_number": sender_number,
            "user_message":  user_message,
        }

    except Exception:
        print("extract_message_data failed:")
        print(traceback.format_exc())
        return None


def mark_message_as_read(message_id: str):
    """
    Sends a 'read' receipt to Meta so the message gets a blue double-tick
    and Meta stops queuing retries for this webhook event.
    """
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return  # Skip silently if env vars are missing.

    url = (
        f"https://graph.facebook.com/{META_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Mark-as-read status: {resp.status_code}")
    except Exception:
        print("mark_message_as_read failed (non-critical):")
        print(traceback.format_exc())


def send_whatsapp_message(to_number: str, message: str):
    """Sends a plain-text reply via the WhatsApp Cloud API."""
    if not WHATSAPP_ACCESS_TOKEN:
        raise ValueError("WHATSAPP_ACCESS_TOKEN is missing.")

    if not WHATSAPP_PHONE_NUMBER_ID:
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID is missing.")

    url = (
        f"https://graph.facebook.com/{META_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message,
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)

    if response.status_code not in (200, 201):
        print(f"WhatsApp API error {response.status_code}: {response.text}")
        raise ValueError(
            f"WhatsApp API failed with status {response.status_code}: {response.text}"
        )

    return response.json()


def is_yes_response(message: str) -> bool:
    """Returns True if the user's message is an affirmative reply."""
    yes_words = {
        "yes", "y", "yeah", "yep", "ok", "okay", "sure",
        "yes please", "haan", "ha", "hanji", "ji", "please",
    }
    return message.lower().strip() in yes_words


def extract_next_question(answer: str):
    """
    Looks for a follow-up question appended by the LLM at the end of its answer.
    Returns the question string if found, otherwise None.
    """
    markers = [
        "Next step:",
        "Follow-up question:",
        "Need more details?",
        "Want to know more?",
        "Shall I explain further?",
    ]
    for marker in markers:
        if marker in answer:
            question = answer.split(marker, 1)[1].strip()
            return question or None
    return None