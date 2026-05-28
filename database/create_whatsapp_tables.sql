-- =====================================================
-- WhatsApp Admin Dashboard Tables
-- For SFT WhatsApp RAG Chatbot
-- =====================================================


-- Table 1: Stores every WhatsApp user/lead
CREATE TABLE IF NOT EXISTS whatsapp_contacts (
    id BIGSERIAL PRIMARY KEY,

    phone VARCHAR(30) UNIQUE NOT NULL,
    name TEXT,
    email TEXT,

    lead_status VARCHAR(50) DEFAULT 'New',
    assigned_to TEXT,

    human_takeover BOOLEAN DEFAULT FALSE,

    last_message TEXT,
    last_message_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- Table 2: Stores full chat history
CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id BIGSERIAL PRIMARY KEY,

    contact_id BIGINT REFERENCES whatsapp_contacts(id) ON DELETE CASCADE,

    phone VARCHAR(30) NOT NULL,

    sender_type VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,

    whatsapp_message_id TEXT,
    status VARCHAR(30) DEFAULT 'saved',

    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- Indexes for faster dashboard loading
CREATE INDEX IF NOT EXISTS idx_whatsapp_contacts_phone
ON whatsapp_contacts(phone);

CREATE INDEX IF NOT EXISTS idx_whatsapp_contacts_last_message_at
ON whatsapp_contacts(last_message_at DESC);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_contact_id
ON whatsapp_messages(contact_id);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_phone
ON whatsapp_messages(phone);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_created_at
ON whatsapp_messages(created_at ASC);


-- check the tables

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('whatsapp_contacts', 'whatsapp_messages');