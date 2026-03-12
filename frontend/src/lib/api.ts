import { getToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Ticket {
  id: string;
  title: string;
  description: string;
  customer_email: string;
  category: string;
  priority: "High" | "Medium" | "Low";
  status: "Open" | "In Progress" | "Resolved";
  ai_reasoning: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedTickets {
  tickets: Ticket[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? getToken() : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Auth
  register(data: { email: string; password: string; full_name: string }) {
    return request("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  login(data: { email: string; password: string }) {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Tickets
  createTicket(data: {
    title: string;
    description: string;
    customer_email: string;
  }) {
    return request<Ticket>("/tickets", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getTickets(params: {
    page?: number;
    per_page?: number;
    status?: string;
    priority?: string;
  }) {
    const query = new URLSearchParams();
    if (params.page) query.set("page", String(params.page));
    if (params.per_page) query.set("per_page", String(params.per_page));
    if (params.status) query.set("status", params.status);
    if (params.priority) query.set("priority", params.priority);
    return request<PaginatedTickets>(`/tickets?${query}`);
  },

  updateTicketStatus(id: string, status: string) {
    return request<Ticket>(`/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  deleteTicket(id: string) {
    return request<void>(`/tickets/${id}`, { method: "DELETE" });
  },
};
