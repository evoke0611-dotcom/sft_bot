import { useEffect, useMemo, useRef, useState } from "react";
import {
  getContacts,
  getMessagesByPhone,
  sendAdminMessage,
  updateHumanTakeover,
  updateLeadStatus,
} from "./api";

import {
  Bot,
  CheckCircle2,
  Headphones,
  MessageCircle,
  Phone,
  RefreshCcw,
  Search,
  Send,
  UserRound,
} from "lucide-react";

const leadStatuses = [
  "New",
  "Human Handover",
  "Hot Lead",
  "Follow Up",
  "Converted",
  "Not Interested",
  "Closed",
];

function normalizePhone(phone) {
  return String(phone || "").replace(/\D/g, "");
}

function formatTime(value) {
  if (!value) return "";

  try {
    return new Date(value).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

function formatDate(value) {
  if (!value) return "";

  try {
    return new Date(value).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
    });
  } catch {
    return "";
  }
}

function getDisplayName(contact) {
  return contact?.name || contact?.phone || "Unknown Contact";
}

function getInitial(contact) {
  if (contact?.name) {
    return contact.name.trim().charAt(0).toUpperCase();
  }

  if (contact?.phone) {
    return contact.phone.slice(-2);
  }

  return "U";
}

function dedupeContactsByPhone(contactList) {
  const map = new Map();

  contactList.forEach((contact) => {
    const normalizedPhone = normalizePhone(contact.phone);

    if (!normalizedPhone) return;
    if (normalizedPhone.toLowerCase() === "string") return;

    const cleanContact = {
      ...contact,
      phone: normalizedPhone,
    };

    const oldContact = map.get(normalizedPhone);

    if (!oldContact) {
      map.set(normalizedPhone, cleanContact);
      return;
    }

    const oldTime = new Date(
      oldContact.last_message_at ||
        oldContact.updated_at ||
        oldContact.created_at ||
        0
    ).getTime();

    const newTime = new Date(
      cleanContact.last_message_at ||
        cleanContact.updated_at ||
        cleanContact.created_at ||
        0
    ).getTime();

    if (newTime > oldTime) {
      map.set(normalizedPhone, cleanContact);
    }
  });

  return Array.from(map.values()).sort((a, b) => {
    const timeA = new Date(
      a.last_message_at || a.updated_at || a.created_at || 0
    ).getTime();

    const timeB = new Date(
      b.last_message_at || b.updated_at || b.created_at || 0
    ).getTime();

    return timeB - timeA;
  });
}

export default function App() {
  const [contacts, setContacts] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState("");
  const [messages, setMessages] = useState([]);

  const [search, setSearch] = useState("");
  const [replyText, setReplyText] = useState("");
  const [notice, setNotice] = useState("");

  const [loadingContacts, setLoadingContacts] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);

  const selectedPhoneRef = useRef("");
  const messagesEndRef = useRef(null);

  const selectedContact = useMemo(() => {
    return (
      contacts.find(
        (contact) => normalizePhone(contact.phone) === selectedPhone
      ) || null
    );
  }, [contacts, selectedPhone]);

  useEffect(() => {
    selectedPhoneRef.current = selectedPhone;
  }, [selectedPhone]);

  async function loadContacts() {
    try {
      const data = await getContacts();
      const uniqueContacts = dedupeContactsByPhone(data);

      setContacts(uniqueContacts);

      const currentPhone = selectedPhoneRef.current;

      if (!currentPhone && uniqueContacts.length > 0) {
        const firstPhone = normalizePhone(uniqueContacts[0].phone);
        setSelectedPhone(firstPhone);
        selectedPhoneRef.current = firstPhone;
        return;
      }

      if (currentPhone) {
        const stillExists = uniqueContacts.some(
          (contact) => normalizePhone(contact.phone) === currentPhone
        );

        if (!stillExists && uniqueContacts.length > 0) {
          const firstPhone = normalizePhone(uniqueContacts[0].phone);
          setSelectedPhone(firstPhone);
          selectedPhoneRef.current = firstPhone;
        }
      }
    } catch (error) {
      console.error(error);
      setNotice("Unable to load contacts. Check backend and admin key.");
    }
  }

  async function loadMessagesBySelectedPhone(phone = selectedPhoneRef.current) {
    const cleanPhone = normalizePhone(phone);

    if (!cleanPhone) return;

    try {
      setLoadingMessages(true);

      const data = await getMessagesByPhone(cleanPhone);
      setMessages(data);
    } catch (error) {
      console.error(error);
      setNotice("Unable to load chat messages.");
    } finally {
      setLoadingMessages(false);
    }
  }

  async function refreshDashboard(showLoader = false) {
    try {
      if (showLoader) setLoadingContacts(true);

      await loadContacts();

      const currentPhone = selectedPhoneRef.current;

      if (currentPhone) {
        await loadMessagesBySelectedPhone(currentPhone);
      }
    } finally {
      if (showLoader) setLoadingContacts(false);
    }
  }

  useEffect(() => {
    refreshDashboard(true);
  }, []);

  useEffect(() => {
    if (selectedPhone) {
      loadMessagesBySelectedPhone(selectedPhone);
    }
  }, [selectedPhone]);

  useEffect(() => {
    const timer = setInterval(() => {
      refreshDashboard(false);
    }, 3000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const filteredContacts = useMemo(() => {
    const term = search.trim().toLowerCase();

    if (!term) return contacts;

    return contacts.filter((contact) => {
      return (
        String(contact.phone || "").toLowerCase().includes(term) ||
        String(contact.name || "").toLowerCase().includes(term) ||
        String(contact.last_message || "").toLowerCase().includes(term) ||
        String(contact.lead_status || "").toLowerCase().includes(term)
      );
    });
  }, [contacts, search]);

  function handleSelectContact(contact) {
    const cleanPhone = normalizePhone(contact?.phone);

    if (!cleanPhone) return;

    setSelectedPhone(cleanPhone);
    selectedPhoneRef.current = cleanPhone;

    setReplyText("");
    setNotice("");
    setMessages([]);

    loadMessagesBySelectedPhone(cleanPhone);
  }

  async function handleTakeoverToggle(event) {
    if (!selectedContact?.phone) return;

    const takeover = event.target.checked;
    const cleanPhone = normalizePhone(selectedContact.phone);

    try {
      const updatedContact = await updateHumanTakeover(cleanPhone, takeover);

      const cleanUpdatedContact = {
        ...updatedContact,
        phone: normalizePhone(updatedContact.phone),
      };

      setContacts((oldContacts) =>
        dedupeContactsByPhone(
          oldContacts.map((contact) =>
            normalizePhone(contact.phone) === cleanUpdatedContact.phone
              ? cleanUpdatedContact
              : contact
          )
        )
      );

      setNotice(
        takeover
          ? "Human takeover ON. Bot will not reply automatically."
          : "Human takeover OFF. Bot can reply automatically."
      );
    } catch (error) {
      console.error(error);
      setNotice("Unable to update human takeover.");
    }
  }

  async function handleStatusChange(event) {
    if (!selectedContact?.phone) return;

    const leadStatus = event.target.value;
    const cleanPhone = normalizePhone(selectedContact.phone);

    try {
      const updatedContact = await updateLeadStatus(cleanPhone, leadStatus);

      const cleanUpdatedContact = {
        ...updatedContact,
        phone: normalizePhone(updatedContact.phone),
      };

      setContacts((oldContacts) =>
        dedupeContactsByPhone(
          oldContacts.map((contact) =>
            normalizePhone(contact.phone) === cleanUpdatedContact.phone
              ? cleanUpdatedContact
              : contact
          )
        )
      );

      setNotice("Lead status updated.");
    } catch (error) {
      console.error(error);
      setNotice("Unable to update lead status.");
    }
  }

  async function handleSendMessage() {
    if (!selectedContact?.phone || !replyText.trim()) return;

    const cleanPhone = normalizePhone(selectedContact.phone);
    const messageToSend = replyText.trim();

    try {
      setSending(true);
      setNotice("");

      await sendAdminMessage(cleanPhone, messageToSend);

      setReplyText("");

      await loadMessagesBySelectedPhone(cleanPhone);
      await loadContacts();

      setNotice("Message sent successfully.");
    } catch (error) {
      console.error(error);
      setNotice(
        "Message could not be sent. Chat view is working, but WhatsApp send API/token needs fixing."
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="whatsapp-app">
      <aside className="chat-sidebar">
        <div className="sidebar-top">
          <div className="brand-box">
            <div className="brand-avatar">SFT</div>
            <div>
              <h1>SFT Chat</h1>
              <p>Admin Dashboard</p>
            </div>
          </div>

          <button className="round-btn" onClick={() => refreshDashboard(true)}>
            <RefreshCcw size={18} />
          </button>
        </div>

        <div className="search-area">
          <Search size={18} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search or start a new chat"
          />
        </div>

        <div className="filter-bar">
          <span className="active-filter">All</span>
          <span>{filteredContacts.length} chats</span>
        </div>

        <div className="contact-list">
          {loadingContacts && contacts.length === 0 && (
            <div className="small-loading">Loading contacts...</div>
          )}

          {!loadingContacts && filteredContacts.length === 0 && (
            <div className="small-loading">No contacts found.</div>
          )}

          {filteredContacts.map((contact) => (
            <button
              key={normalizePhone(contact.phone)}
              className={
                selectedPhone === normalizePhone(contact.phone)
                  ? "contact-item active"
                  : "contact-item"
              }
              onClick={() => handleSelectContact(contact)}
            >
              <div className="contact-avatar">{getInitial(contact)}</div>

              <div className="contact-info">
                <div className="contact-row">
                  <h3>{getDisplayName(contact)}</h3>
                  <span>{formatTime(contact.last_message_at)}</span>
                </div>

                <div className="contact-row bottom">
                  <p>{contact.last_message || "No message yet"}</p>
                </div>

                <div className="contact-tags">
                  <span className="lead-chip">
                    {contact.lead_status || "New"}
                  </span>

                  {contact.human_takeover && (
                    <span className="human-chip">Human</span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="chat-main">
        {!selectedContact ? (
          <div className="no-chat">
            <MessageCircle size={70} />
            <h2>SFT WhatsApp Admin</h2>
            <p>Select a chat from the left side to view messages.</p>
          </div>
        ) : (
          <>
            <header className="chat-header">
              <div className="header-left">
                <div className="contact-avatar large">
                  {getInitial(selectedContact)}
                </div>

                <div>
                  <h2>{getDisplayName(selectedContact)}</h2>
                  <p>
                    <Phone size={14} />
                    {selectedContact.phone}
                  </p>
                </div>
              </div>

              <div className="header-actions">
                <label className="takeover-toggle">
                  <span>Human takeover</span>
                  <input
                    type="checkbox"
                    checked={Boolean(selectedContact.human_takeover)}
                    onChange={handleTakeoverToggle}
                  />
                </label>

                <select
                  value={selectedContact.lead_status || "New"}
                  onChange={handleStatusChange}
                >
                  {leadStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
            </header>

            {notice && <div className="notice-box">{notice}</div>}

            <section className="message-area">
              {loadingMessages && messages.length === 0 ? (
                <div className="chat-loading">Loading chat...</div>
              ) : messages.length === 0 ? (
                <div className="chat-loading">No messages yet.</div>
              ) : (
                <>
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`message-line ${message.sender_type}`}
                    >
                      <div className="message-card">
                        <div className="sender-label">
                          {message.sender_type === "user" && (
                            <>
                              <UserRound size={13} /> Customer
                            </>
                          )}

                          {message.sender_type === "bot" && (
                            <>
                              <Bot size={13} /> Bot
                            </>
                          )}

                          {message.sender_type === "admin" && (
                            <>
                              <Headphones size={13} /> Admin
                            </>
                          )}
                        </div>

                        <div className="message-text">
                          {message.message_text}
                        </div>

                        <div className="message-meta">
                          <span>{formatDate(message.created_at)}</span>
                          <span>{formatTime(message.created_at)}</span>

                          {(message.sender_type === "bot" ||
                            message.sender_type === "admin") && (
                            <CheckCircle2 size={13} />
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  <div ref={messagesEndRef} />
                </>
              )}
            </section>

            <footer className="reply-footer">
              <input
                value={replyText}
                onChange={(event) => setReplyText(event.target.value)}
                placeholder="Type a message"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    handleSendMessage();
                  }
                }}
              />

              <button
                className="send-button"
                onClick={handleSendMessage}
                disabled={sending || !replyText.trim()}
              >
                <Send size={20} />
              </button>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}