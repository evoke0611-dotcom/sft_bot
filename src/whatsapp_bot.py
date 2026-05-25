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

















# """
# whatsapp_bot.py  —  drop-in replacement for your existing src/whatsapp_bot.py
# Vercel serverless entry point. Replaces FastAPI with BaseHTTPRequestHandler.

# Place this file at:  src/whatsapp_bot.py  (same location as before)

# Vercel exposes it at:
#   GET  /api/whatsapp_bot  →  Meta webhook verification
#   POST /api/whatsapp_bot  →  Incoming WhatsApp messages
# """

# import os
# import json
# import traceback
# import requests

# from http.server import BaseHTTPRequestHandler
# from urllib.parse import urlparse, parse_qs

# from src.retriever import retrieve, generate_openai_answer


# # ── Env vars ─────────────────────────────────────────────────────────────────
# WHATSAPP_VERIFY_TOKEN    = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "").strip()
# WHATSAPP_ACCESS_TOKEN    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
# WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
# META_API_VERSION         = os.getenv("META_API_VERSION", "v21.0")

# # ── In-process dedup (lives for one warm Vercel instance) ────────────────────
# _processed_ids: set = set()


# class handler(BaseHTTPRequestHandler):
#     """Vercel calls this class for every request."""

#     def log_message(self, format, *args):
#         pass  # suppress default stderr noise

#     # ── GET → Meta webhook verification ──────────────────────────────────────
#     def do_GET(self):
#         try:
#             params    = parse_qs(urlparse(self.path).query)
#             mode      = params.get("hub.mode",         [None])[0]
#             token     = params.get("hub.verify_token", [None])[0]
#             challenge = params.get("hub.challenge",    [None])[0]

#             if mode == "subscribe" and token and token.strip() == WHATSAPP_VERIFY_TOKEN:
#                 self._send(200, challenge, "text/plain")
#             else:
#                 print(f"Webhook verify failed. mode={mode} token={token!r}")
#                 self._send(403, "Verification failed")

#         except Exception:
#             print(traceback.format_exc())
#             self._send(500, "Internal error")

#     # ── POST → incoming WhatsApp message ─────────────────────────────────────
#     def do_POST(self):
#         # Always return 200 — otherwise Meta retries the same message forever.
#         try:
#             length = int(self.headers.get("Content-Length", 0))
#             body   = self.rfile.read(length) if length else b""
#             data   = json.loads(body) if body else {}

#             print("=== Incoming webhook ===")
#             print(json.dumps(data, indent=2))
#             print("========================")

#             # Skip status-update events (delivery/read receipts — no "messages" key)
#             entries = data.get("entry", [])
#             if entries:
#                 value = entries[0].get("changes", [{}])[0].get("value", {})
#                 if "statuses" in value and "messages" not in value:
#                     print("Status update event — skipping.")
#                     self._send(200, "ok")
#                     return

#             msg = _extract_message(data)
#             if not msg:
#                 print("No user message in payload.")
#                 self._send(200, "ok")
#                 return

#             message_id = msg["message_id"]
#             sender     = msg["sender_number"]
#             user_text  = msg["user_message"]

#             # Dedup — avoid double replies if Meta sends same webhook twice
#             if message_id in _processed_ids:
#                 print(f"Duplicate {message_id} — skipping.")
#                 self._send(200, "ok")
#                 return
#             _processed_ids.add(message_id)

#             # Blue double-tick + stops Meta from re-queuing this event
#             _mark_as_read(message_id)

#             print(f"Sender : {sender}")
#             print(f"Message: {user_text!r}")

#             if not user_text:
#                 _send_message(sender, "Please type your question clearly.")
#                 self._send(200, "ok")
#                 return

#             # ── RAG pipeline ──────────────────────────────────────────────
#             results = retrieve(user_text, top_k=5)
#             print(f"Retrieved {len(results)} chunks from pgvector.")

#             if not results:
#                 answer = "Our call adviser will connect with you shortly."
#             else:
#                 answer = generate_openai_answer(user_text, results)

#             print(f"Answer ({len(answer)} chars): {answer[:100]}...")

#             _send_message(sender, answer[:3500])
#             self._send(200, "ok")

#         except Exception:
#             print("POST /webhook error:")
#             print(traceback.format_exc())
#             self._send(200, "ok")   # still 200 so Meta does not retry

#     # ── helper ───────────────────────────────────────────────────────────────
#     def _send(self, status: int, body: str, content_type="application/json"):
#         encoded = body.encode("utf-8")
#         self.send_response(status)
#         self.send_header("Content-Type", content_type)
#         self.send_header("Content-Length", str(len(encoded)))
#         self.end_headers()
#         self.wfile.write(encoded)


# # ── Pure helper functions ─────────────────────────────────────────────────────

# def _extract_message(data: dict):
#     """Pull sender, message_id and text body from a WhatsApp Cloud API payload."""
#     try:
#         value    = data["entry"][0]["changes"][0]["value"]
#         messages = value.get("messages", [])
#         if not messages:
#             return None

#         msg      = messages[0]
#         msg_type = msg.get("type")

#         if msg_type == "text":
#             text = msg.get("text", {}).get("body", "").strip()
#         else:
#             print(f"Unsupported message type: {msg_type!r}")
#             text = ""

#         return {
#             "message_id":    msg.get("id"),
#             "sender_number": msg.get("from"),
#             "user_message":  text,
#         }

#     except Exception:
#         print("_extract_message error:")
#         print(traceback.format_exc())
#         return None


# def _mark_as_read(message_id: str):
#     """Send read receipt so Meta stops retrying this webhook event."""
#     if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
#         return
#     try:
#         requests.post(
#             f"https://graph.facebook.com/{META_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
#             headers={
#                 "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
#                 "Content-Type":  "application/json",
#             },
#             json={
#                 "messaging_product": "whatsapp",
#                 "status":     "read",
#                 "message_id": message_id,
#             },
#             timeout=8,
#         )
#     except Exception:
#         print("_mark_as_read failed (non-critical):")
#         print(traceback.format_exc())


# def _send_message(to: str, body: str):
#     """Send a plain-text WhatsApp reply via Cloud API."""
#     if not WHATSAPP_ACCESS_TOKEN:
#         raise ValueError("WHATSAPP_ACCESS_TOKEN missing.")
#     if not WHATSAPP_PHONE_NUMBER_ID:
#         raise ValueError("WHATSAPP_PHONE_NUMBER_ID missing.")

#     resp = requests.post(
#         f"https://graph.facebook.com/{META_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
#         headers={
#             "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
#             "Content-Type":  "application/json",
#         },
#         json={
#             "messaging_product": "whatsapp",
#             "to":   to,
#             "type": "text",
#             "text": {"preview_url": False, "body": body},
#         },
#         timeout=20,
#     )
#     if resp.status_code not in (200, 201):
#         raise ValueError(f"WhatsApp API error {resp.status_code}: {resp.text}")
#     return resp.json()





"""
src/whatsapp_bot.py  —  Vercel serverless handler
"""

import os
import json
import traceback
import requests

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from src.retriever import retrieve, generate_openai_answer


WHATSAPP_VERIFY_TOKEN    = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "").strip()
WHATSAPP_ACCESS_TOKEN    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
META_API_VERSION         = os.getenv("META_API_VERSION", "v21.0")

_processed_ids: set = set()


class handler_old(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            parsed  = urlparse(self.path)
            params  = parse_qs(parsed.query)
            path    = parsed.path

            mode      = params.get("hub.mode",         [None])[0]
            token     = params.get("hub.verify_token", [None])[0]
            challenge = params.get("hub.challenge",    [None])[0]

            # ── Debug endpoint: visit /debug to check token values ──────────
            if path == "/debug":
                info = json.dumps({
                    "env_token_loaded":  bool(WHATSAPP_VERIFY_TOKEN),
                    "env_token_length":  len(WHATSAPP_VERIFY_TOKEN),
                    "env_token_value":   WHATSAPP_VERIFY_TOKEN,   # visible for debugging
                    "received_mode":     mode,
                    "received_token":    token,
                    "received_challenge": challenge,
                    "full_path":         self.path,
                }, indent=2)
                self._send(200, info)
                return

            # ── Normal Meta verification ────────────────────────────────────
            print(f"[VERIFY] mode={mode!r} token={token!r} env_token={WHATSAPP_VERIFY_TOKEN!r}")

            if mode == "subscribe" and token and token.strip() == WHATSAPP_VERIFY_TOKEN:
                self._send(200, challenge, "text/plain")
            else:
                self._send(403, json.dumps({
                    "error":            "Verification failed",
                    "reason":           "token mismatch or missing params",
                    "received_mode":    mode,
                    "received_token":   token,
                    "env_token_set":    bool(WHATSAPP_VERIFY_TOKEN),
                    "env_token_length": len(WHATSAPP_VERIFY_TOKEN),
                }))

        except Exception:
            print(traceback.format_exc())
            self._send(500, "Internal error")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length) if length else b""
            data   = json.loads(body) if body else {}

            print("=== Incoming webhook ===")
            print(json.dumps(data, indent=2))
            print("========================")

            entries = data.get("entry", [])
            if entries:
                value = entries[0].get("changes", [{}])[0].get("value", {})
                if "statuses" in value and "messages" not in value:
                    print("Status update — skipping.")
                    self._send(200, "ok")
                    return

            msg = _extract_message(data)
            if not msg:
                print("No user message in payload.")
                self._send(200, "ok")
                return

            message_id = msg["message_id"]
            sender     = msg["sender_number"]
            user_text  = msg["user_message"]

            if message_id in _processed_ids:
                print(f"Duplicate {message_id} — skipping.")
                self._send(200, "ok")
                return
            _processed_ids.add(message_id)

            _mark_as_read(message_id)

            print(f"Sender : {sender}")
            print(f"Message: {user_text!r}")

            if not user_text:
                _send_message(sender, "Please type your question clearly.")
                self._send(200, "ok")
                return

            results = retrieve(user_text, top_k=5)
            print(f"Retrieved {len(results)} chunks from pgvector.")

            if not results:
                answer = "Our call adviser will connect with you shortly."
            else:
                answer = generate_openai_answer(user_text, results)

            print(f"Answer ({len(answer)} chars): {answer[:100]}...")

            _send_message(sender, answer[:3500])
            self._send(200, "ok")

        except Exception:
            print("POST error:")
            print(traceback.format_exc())
            self._send(200, "ok")

    def _send(self, status: int, body: str, content_type="application/json"):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _extract_message(data: dict):
    try:
        value    = data["entry"][0]["changes"][0]["value"]
        messages = value.get("messages", [])
        if not messages:
            return None

        msg      = messages[0]
        msg_type = msg.get("type")

        if msg_type == "text":
            text = msg.get("text", {}).get("body", "").strip()
        else:
            print(f"Unsupported message type: {msg_type!r}")
            text = ""

        return {
            "message_id":    msg.get("id"),
            "sender_number": msg.get("from"),
            "user_message":  text,
        }
    except Exception:
        print("_extract_message error:")
        print(traceback.format_exc())
        return None


def _mark_as_read(message_id: str):
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return
    try:
        requests.post(
            f"https://graph.facebook.com/{META_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "status": "read", "message_id": message_id},
            timeout=8,
        )
    except Exception:
        print("_mark_as_read failed:")
        print(traceback.format_exc())


def _send_message(to: str, body: str):
    if not WHATSAPP_ACCESS_TOKEN:
        raise ValueError("WHATSAPP_ACCESS_TOKEN missing.")
    if not WHATSAPP_PHONE_NUMBER_ID:
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID missing.")

    resp = requests.post(
        f"https://graph.facebook.com/{META_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"},
        json={"messaging_product": "whatsapp", "to": to, "type": "text",
              "text": {"preview_url": False, "body": body}},
        timeout=20,
    )
    if resp.status_code not in (200, 201):
        raise ValueError(f"WhatsApp API error {resp.status_code}: {resp.text}")
    return resp.json()