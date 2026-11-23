/**
 * NyayaAI API client — calls FastAPI backend via Caddy gateway.
 *
 * All requests go to relative path `/api/...` with `XTransformPort=8000`
 * so Caddy forwards them to the Python FastAPI backend on port 8000.
 */

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function apiUrl(path: string): string {
  return `${BACKEND_URL}${path}`;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("nyayaai_token");
}

function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem("nyayaai_token", token);
  } else {
    localStorage.removeItem("nyayaai_token");
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  // Don't set Content-Type for FormData (browser sets boundary automatically)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(apiUrl(path), { ...options, headers });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

// ===== Types =====
export interface User {
  id: string;
  email: string;
  name: string | null;
  role: string;
  preferred_language: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string | null;
  file_size: number | null;
  status: string;
  doc_type: string | null;
  summary: string | null;
  plain_explanation: string | null;
  deadlines: any[];
  key_entities: any[];
  missing_info: any[];
  ocr_text: string | null;
  error: string | null;
  created_at: string;
  analyzed_at: string | null;
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  sources: any[];
  created_at: string;
}

export interface Chat {
  id: string;
  title: string;
  created_at: string;
  messages: ChatMessage[];
}

export interface WorkflowStep {
  step: number;
  title: string;
  description: string;
  deadline_days: number | null;
  priority: string;
}

export interface Workflow {
  case_type: string;
  summary: string;
  steps: WorkflowStep[];
  checklist: string[];
  prep_score: number;
}

export interface DraftTemplateField {
  name: string;
  label: string;
  required: boolean;
  textarea?: boolean;
}

export interface DraftTemplate {
  label: string;
  description: string;
  fields: DraftTemplateField[];
}

export interface Draft {
  id: string;
  draft_type: string;
  title: string;
  content: string;
  created_at: string;
}

// ===== API =====
export const api = {
  // Auth
  signup: (email: string, password: string, name?: string) =>
    request<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/api/auth/me"),

  logout: () => setToken(null),

  // Documents
  uploadDocument: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<DocumentItem>("/api/documents/upload", {
      method: "POST",
      body: fd,
    });
  },

  listDocuments: () => request<DocumentItem[]>("/api/documents"),

  getDocument: (id: string) => request<DocumentItem>(`/api/documents/${id}`),

  reanalyze: (id: string) =>
    request<{ message: string }>(`/api/documents/${id}/reanalyze`, {
      method: "POST",
    }),

  // Chat
  listChats: () => request<Chat[]>("/api/chat"),
  createChat: (title: string) =>
    request<Chat>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  getChat: (id: string) => request<Chat>(`/api/chat/${id}`),
  sendMessage: (chatId: string, content: string) =>
    request<ChatMessage>("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ chat_id: chatId, content }),
    }),
  deleteChat: (id: string) =>
    request<{ message: string }>(`/api/chat/${id}`, { method: "DELETE" }),

  // Tools
  generateWorkflow: (data: {
    document_id?: string;
    description?: string;
    case_type_hint?: string;
  }) =>
    request<Workflow>("/api/tools/workflow", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listDraftTemplates: () =>
    request<Record<string, DraftTemplate>>("/api/tools/drafts/templates"),

  createDraft: (draft_type: string, title: string, fields: Record<string, string>) =>
    request<Draft>("/api/tools/drafts", {
      method: "POST",
      body: JSON.stringify({ draft_type, title, fields }),
    }),

  listDrafts: () => request<Draft[]>("/api/tools/drafts"),
};
