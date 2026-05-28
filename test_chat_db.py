from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(".env"), override=True)

from src.chat_db import get_or_create_contact, save_message, is_human_takeover


phone = "919999999999"

contact = get_or_create_contact(phone)

print("Contact created/found:")
print(contact)

save_message(
    contact_id=contact["id"],
    phone=phone,
    sender_type="user",
    message_text="Test message from database connection",
    whatsapp_message_id="test_123",
    status="received"
)

print("Message saved successfully")

takeover = is_human_takeover(phone)
print("Human takeover:", takeover)