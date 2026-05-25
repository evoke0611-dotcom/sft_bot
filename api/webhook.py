"""
api/webhook.py  —  Vercel serverless entry point
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


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            parsed    = urlparse(self.path)
            params    = parse_qs(parsed.query)
            path      = parsed.path

            mode      = params.get("hub.mode",         [None])[0]
            token     = params.get("hub.verify_token", [None])[0]
            challenge = params.get("hub.challenge",    [None])[0]

            if path == "/debug":
                info = json.dumps({
                    "env_token_loaded":   bool(WHATSAPP_VERIFY_TOKEN),
                    "env_token_length":   len(WHATSAPP_VERIFY_TOKEN),
                    "env_token_value":    WHATSAPP_VERIFY_TOKEN,
                    "received_mode":      mode,
                    "received_token":     token,
                    "received_challenge": challenge,
                    "full_path":          self.path,
                }, indent=2)
                self._send(200, info)
                return

            print(f"[VERIFY] mode={mode!r} token={token!r} env={WHATSAPP_VERIFY_TOKEN!r}")

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
                self._send(200, "ok")
                return

            message_id = msg["message_id"]
            sender     = msg["sender_number"]
            user_text  = msg["user_message"]

            if message_id in _processed_ids:
                self._send(200, "ok")
                return
            _processed_ids.add(message_id)

            _mark_as_read(message_id)

            if not user_text:
                _send_message(sender, "Please type your question clearly.")
                self._send(200, "ok")
                return

            results = retrieve(user_text, top_k=5)

            if not results:
                answer = "Our call adviser will connect with you shortly."
            else:
                answer = generate_openai_answer(user_text, results)

            _send_message(sender, answer[:3500])
            self._send(200, "ok")

        except Exception:
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
            text = ""

        return {
            "message_id":    msg.get("id"),
            "sender_number": msg.get("from"),
            "user_message":  text,
        }
    except Exception:
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