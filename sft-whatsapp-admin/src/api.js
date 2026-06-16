import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    "x-admin-key": ADMIN_API_KEY,
  },
});

export async function getContacts() {
  const response = await api.get("/admin/contacts");
  return response.data.contacts || [];
}

export async function getMessagesByPhone(phone) {
  const safePhone = encodeURIComponent(phone);
  const response = await api.get(`/admin/messages-by-phone/${safePhone}`);
  return response.data.messages || [];
}

export async function updateHumanTakeover(phone, takeover) {
  const safePhone = encodeURIComponent(phone);

  const response = await api.patch(`/admin/contact/${safePhone}/human-takeover`, {
    takeover,
  });

  return response.data.contact;
}

export async function updateLeadStatus(phone, leadStatus) {
  const safePhone = encodeURIComponent(phone);

  const response = await api.patch(`/admin/contact/${safePhone}/status`, {
    lead_status: leadStatus,
  });

  return response.data.contact;
}

export async function sendAdminMessage(phone, message) {
  const response = await api.post("/admin/send-message", {
    phone,
    message,
  });

  return response.data;
}