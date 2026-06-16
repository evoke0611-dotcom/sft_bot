import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"), override=True)

TOKEN = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
PHONE_NUMBER_ID = (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
META_API_VERSION = (os.getenv("META_API_VERSION") or "v21.0").strip()

print("Token loaded:", bool(TOKEN))
print("Token length:", len(TOKEN))
print("Token starts with:", TOKEN[:10])
print("Phone number ID:", PHONE_NUMBER_ID)
print("Meta API version:", META_API_VERSION)

url = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

params = {
    "fields": "id,display_phone_number,verified_name"
}

response = requests.get(url, headers=headers, params=params, timeout=20)

print("Status code:", response.status_code)
print("Response:")
print(response.text)