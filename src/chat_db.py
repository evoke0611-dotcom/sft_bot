import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """
    Create database connection using DATABASE_URL from .env
    """

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing in .env file")

    return psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor
    )


def get_or_create_contact(phone: str):
    """
    Check if WhatsApp contact already exists.
    If not, create new contact.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM whatsapp_contacts
        WHERE phone = %s
        """,
        (phone,)
    )

    contact = cur.fetchone()

    if contact:
        cur.close()
        conn.close()
        return contact

    cur.execute(
        """
        INSERT INTO whatsapp_contacts (phone, lead_status, human_takeover)
        VALUES (%s, %s, %s)
        RETURNING *
        """,
        (phone, "New", False)
    )

    contact = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return contact


def save_message(
    contact_id,
    phone: str,
    sender_type: str,
    message_text: str,
    whatsapp_message_id=None,
    status: str = "saved"
):
    """
    Save user, bot, or admin message in whatsapp_messages table.
    Also update last message in whatsapp_contacts table.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO whatsapp_messages
        (
            contact_id,
            phone,
            sender_type,
            message_text,
            whatsapp_message_id,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            contact_id,
            phone,
            sender_type,
            message_text,
            whatsapp_message_id,
            status
        )
    )

    cur.execute(
        """
        UPDATE whatsapp_contacts
        SET last_message = %s,
            last_message_at = NOW(),
            updated_at = NOW()
        WHERE id = %s
        """,
        (message_text, contact_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def is_human_takeover(phone: str) -> bool:
    """
    Check whether human takeover is ON for this WhatsApp user.
    If ON, bot should not reply automatically.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT human_takeover
        FROM whatsapp_contacts
        WHERE phone = %s
        """,
        (phone,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return False

    return bool(row["human_takeover"])


def set_human_takeover(phone: str, takeover: bool = True):
    """
    Turn human takeover ON or OFF for a WhatsApp user.

    takeover=True  means bot will stop replying automatically.
    takeover=False means bot can reply automatically again.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE whatsapp_contacts
        SET human_takeover = %s,
            lead_status = CASE
                WHEN %s = TRUE THEN 'Human Handover'
                ELSE lead_status
            END,
            updated_at = NOW()
        WHERE phone = %s
        RETURNING *
        """,
        (takeover, takeover, phone)
    )

    updated_contact = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return updated_contact


def update_lead_status(phone: str, lead_status: str):
    """
    Update lead status manually from dashboard later.
    Example: New, Hot Lead, Follow Up, Converted, Closed.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE whatsapp_contacts
        SET lead_status = %s,
            updated_at = NOW()
        WHERE phone = %s
        RETURNING *
        """,
        (lead_status, phone)
    )

    updated_contact = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return updated_contact

def get_all_contacts():
    """
    Get WhatsApp contacts for admin dashboard.
    Same phone number will appear only once.
    Contacts with no real phone/string test data are ignored.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            phone,
            name,
            email,
            lead_status,
            assigned_to,
            human_takeover,
            last_message,
            last_message_at,
            created_at,
            updated_at
        FROM whatsapp_contacts
        WHERE phone IS NOT NULL
          AND TRIM(phone) <> ''
          AND LOWER(TRIM(phone)) <> 'string'
        ORDER BY COALESCE(last_message_at, updated_at, created_at) DESC
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    unique_contacts = {}

    for contact in rows:
        raw_phone = str(contact.get("phone") or "")
        clean_phone = "".join(ch for ch in raw_phone if ch.isdigit())

        if not clean_phone:
            continue

        existing_contact = unique_contacts.get(clean_phone)

        if not existing_contact:
            contact["phone"] = clean_phone
            unique_contacts[clean_phone] = contact
            continue

        old_time = (
            existing_contact.get("last_message_at")
            or existing_contact.get("updated_at")
            or existing_contact.get("created_at")
        )

        new_time = (
            contact.get("last_message_at")
            or contact.get("updated_at")
            or contact.get("created_at")
        )

        if new_time and old_time and new_time > old_time:
            contact["phone"] = clean_phone
            unique_contacts[clean_phone] = contact

    contacts = list(unique_contacts.values())

    contacts.sort(
        key=lambda item: (
            item.get("last_message_at")
            or item.get("updated_at")
            or item.get("created_at")
        ),
        reverse=True,
    )

    return contacts

def get_messages_by_contact(contact_id: int):
    """
    Get full chat history for one contact.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            contact_id,
            phone,
            sender_type,
            message_text,
            whatsapp_message_id,
            status,
            created_at
        FROM whatsapp_messages
        WHERE contact_id = %s
        ORDER BY created_at ASC
        """,
        (contact_id,)
    )

    messages = cur.fetchall()

    cur.close()
    conn.close()

    return messages

def get_contact_by_phone(phone: str):
    """
    Get one contact by phone number.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM whatsapp_contacts
        WHERE phone = %s
        """,
        (phone,)
    )

    contact = cur.fetchone()

    cur.close()
    conn.close()

    return contact

def get_messages_by_phone(phone: str):
    """
    Get full chat history for one WhatsApp phone number.
    This is better for dashboard because one phone should show one full conversation.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            contact_id,
            phone,
            sender_type,
            message_text,
            whatsapp_message_id,
            status,
            created_at
        FROM whatsapp_messages
        WHERE phone = %s
        ORDER BY created_at ASC
        """,
        (phone,)
    )

    messages = cur.fetchall()

    cur.close()
    conn.close()

    return messages