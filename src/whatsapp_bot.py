# import os
# import requests
# from dotenv import load_dotenv
# from fastapi import FastAPI, Request, HTTPException
# from fastapi.responses import PlainTextResponse

# from src.retriever import retrieve, generate_openai_answer


# load_dotenv()

# app = FastAPI()


# WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
# WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
# WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
# META_API_VERSION = os.getenv("META_API_VERSION", "v21.0")


# # Temporary memory while server is running
# # Later you can store this in PostgreSQL or Redis
# user_followups = {}
# processed_message_ids = set()


# @app.get("/")
# def home():
#     return {
#         "status": "running",
#         "message": "SFT WhatsApp RAG chatbot is active"
#     }


# @app.get("/webhook")
# async def verify_webhook(request: Request):
#     """
#     Meta webhook verification.
#     Meta sends hub.challenge.
#     We must return hub.challenge if verify token is correct.
#     """

#     params = request.query_params

#     mode = params.get("hub.mode")
#     token = params.get("hub.verify_token")
#     challenge = params.get("hub.challenge")

#     if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
#         return PlainTextResponse(content=challenge, status_code=200)

#     raise HTTPException(status_code=403, detail="Webhook verification failed")


# @app.post("/webhook")
# async def receive_whatsapp_message(request: Request):
#     """
#     Receives WhatsApp messages,
#     sends them to RAG pipeline,
#     and replies back on WhatsApp.
#     """

#     data = await request.json()

#     try:
#         message_data = extract_message_data(data)

#         if not message_data:
#             return {"status": "no user message found"}

#         message_id = message_data["message_id"]
#         sender_number = message_data["sender_number"]
#         user_message = message_data["user_message"]

#         # Avoid duplicate replies if Meta sends same webhook again
#         if message_id in processed_message_ids:
#             return {"status": "duplicate message ignored"}

#         processed_message_ids.add(message_id)

#         if not user_message:
#             send_whatsapp_message(
#                 sender_number,
#                 "Please type your question clearly."
#             )
#             return {"status": "empty message handled"}

#         # If user replies yes, use the previous next-step question
#         user_question = user_message

#         if is_yes_response(user_message) and sender_number in user_followups:
#             user_question = user_followups[sender_number]
#             del user_followups[sender_number]

#         print(f"User number: {sender_number}")
#         print(f"User question: {user_question}")

#         # Step 1: Retrieve from your PostgreSQL vector database
#         results = retrieve(user_question, top_k=5)

#         if not results:
#             answer = "Our call adviser will connect with you shortly."
#         else:
#             # Step 2: Generate short answer using OpenAI
#             answer = generate_openai_answer(user_question, results)

#         # Save next-step/follow-up question for "yes" reply
#         next_question = extract_next_question(answer)

#         if next_question:
#             user_followups[sender_number] = next_question

#         # WhatsApp message safety limit
#         answer = answer[:3500]

#         send_whatsapp_message(sender_number, answer)

#         return {"status": "message processed"}

#     except Exception as e:
#         print("Webhook error:", str(e))
#         return {
#             "status": "error",
#             "detail": str(e)
#         }


# def extract_message_data(data: dict):
#     """
#     Extracts useful data from WhatsApp webhook payload.
#     Handles normal text messages.
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
#     Sends text message to WhatsApp user using Meta Cloud API.
#     """

#     if not WHATSAPP_ACCESS_TOKEN:
#         raise ValueError("WHATSAPP_ACCESS_TOKEN is missing in .env")

#     if not WHATSAPP_PHONE_NUMBER_ID:
#         raise ValueError("WHATSAPP_PHONE_NUMBER_ID is missing in .env")

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
#         print(response.status_code)
#         print(response.text)

#     return response.json()


# def is_yes_response(message: str) -> bool:
#     """
#     Checks whether user replied yes.
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
#     Extracts the next-step question from answer.
#     Works with:
#     Next step:
#     Follow-up question:
#     Need more details?
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
import requests
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

from src.retriever import retrieve, generate_openai_answer


load_dotenv()


WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
META_API_VERSION = os.getenv("META_API_VERSION", "v21.0")


# Temporary memory while server is running
# Later you can store this in PostgreSQL or Redis
user_followups = {}
processed_message_ids = set()


# ── Load embedder ONCE on startup ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.embedder import Embedder
    print("⏳ Loading embedder model...")
    app.state.embedder = Embedder()
    print("✅ Embedder ready!")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def home():
    return {
        "status": "running",
        "message": "SFT WhatsApp RAG chatbot is active"
    }


# ── NEW: Test endpoint visible in Swagger UI ───────────────────────
@app.get("/query", tags=["Testing"])
def query_endpoint(
    q: str = Query(..., description="Type your question here")
):
    """
    Test the RAG pipeline directly from Swagger UI.
    No WhatsApp needed. Model is already loaded — no reload on each call.
    """
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

    return {
        "question": q,
        "answer": answer,
        "sources": sources,
    }


@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Meta webhook verification.
    Meta sends hub.challenge.
    We must return hub.challenge if verify token is correct.
    """

    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """
    Receives WhatsApp messages,
    sends them to RAG pipeline,
    and replies back on WhatsApp.
    """

    data = await request.json()

    try:
        message_data = extract_message_data(data)

        if not message_data:
            return {"status": "no user message found"}

        message_id = message_data["message_id"]
        sender_number = message_data["sender_number"]
        user_message = message_data["user_message"]

        # Avoid duplicate replies if Meta sends same webhook again
        if message_id in processed_message_ids:
            return {"status": "duplicate message ignored"}

        processed_message_ids.add(message_id)

        if not user_message:
            send_whatsapp_message(
                sender_number,
                "Please type your question clearly."
            )
            return {"status": "empty message handled"}

        # If user replies yes, use the previous next-step question
        user_question = user_message

        if is_yes_response(user_message) and sender_number in user_followups:
            user_question = user_followups[sender_number]
            del user_followups[sender_number]

        print(f"User number: {sender_number}")
        print(f"User question: {user_question}")

        # Step 1: Retrieve from your PostgreSQL vector database
        results = retrieve(user_question, top_k=5)

        if not results:
            answer = "Our call adviser will connect with you shortly."
        else:
            # Step 2: Generate short answer using OpenAI
            answer = generate_openai_answer(user_question, results)

        # Save next-step/follow-up question for "yes" reply
        next_question = extract_next_question(answer)

        if next_question:
            user_followups[sender_number] = next_question

        # WhatsApp message safety limit
        answer = answer[:3500]

        send_whatsapp_message(sender_number, answer)

        return {"status": "message processed"}

    except Exception as e:
        print("Webhook error:", str(e))
        return {
            "status": "error",
            "detail": str(e)
        }


def extract_message_data(data: dict):
    """
    Extracts useful data from WhatsApp webhook payload.
    Handles normal text messages.
    """

    try:
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})

        messages = value.get("messages", [])

        if not messages:
            return None

        message = messages[0]

        message_id = message.get("id")
        sender_number = message.get("from")
        message_type = message.get("type")

        if message_type == "text":
            user_message = message.get("text", {}).get("body", "").strip()
        else:
            user_message = ""

        return {
            "message_id": message_id,
            "sender_number": sender_number,
            "user_message": user_message
        }

    except Exception:
        return None


def send_whatsapp_message(to_number: str, message: str):
    """
    Sends text message to WhatsApp user using Meta Cloud API.
    """

    if not WHATSAPP_ACCESS_TOKEN:
        raise ValueError("WHATSAPP_ACCESS_TOKEN is missing in .env")

    if not WHATSAPP_PHONE_NUMBER_ID:
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID is missing in .env")

    url = (
        f"https://graph.facebook.com/{META_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)

    if response.status_code not in [200, 201]:
        print("WhatsApp API error:")
        print(response.status_code)
        print(response.text)

    return response.json()


def is_yes_response(message: str) -> bool:
    """
    Checks whether user replied yes.
    """

    yes_words = [
        "yes",
        "y",
        "yeah",
        "yep",
        "ok",
        "okay",
        "sure",
        "yes please",
        "haan",
        "ha",
        "hanji",
        "ji",
        "please"
    ]

    return message.lower().strip() in yes_words


def extract_next_question(answer: str):
    """
    Extracts the next-step question from answer.
    Works with:
    Next step:
    Follow-up question:
    Need more details?
    """

    markers = [
        "Next step:",
        "Follow-up question:",
        "Need more details?",
        "Want to know more?",
        "Shall I explain further?"
    ]

    for marker in markers:
        if marker in answer:
            question = answer.split(marker, 1)[1].strip()
            return question if question else None

    return None