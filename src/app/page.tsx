'use client';

import { useEffect, useState, useCallback } from "react";
import { api, type User, type DocumentItem, type Chat, type ChatMessage, type ChatStatus, type Workflow, type DraftTemplate, type Draft } from "@/lib/api";

type Tab = "documents" | "chat" | "workflow" | "drafts";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("documents");
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Restore session
  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("nyayaai_token") : null;
    if (token) {
      api.me().then(setUser).catch(() => {
        localStorage.removeItem("nyayaai_token");
        setUser(null);
      });
    }
  }, []);

  const handleAuth = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = authMode === "login"
        ? await api.login(email, password)
        : await api.signup(email, password, name || undefined);
      localStorage.setItem("nyayaai_token", res.access_token);
      setUser(res.user);
    } catch (err: any) {
      setAuthError(err.message || "Authentication failed");
    } finally {
      setAuthLoading(false);
    }
  }, [authMode, email, password, name]);

  const handleLogout = useCallback(() => {
    api.logout();
    setUser(null);
    setEmail("");
    setPassword("");
    setName("");
  }, []);

  if (!user) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-white rounded-lg shadow-sm border border-stone-200 p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-serif font-bold text-stone-800">NyayaAI</h1>
            <p className="text-sm text-stone-500 mt-2">AI-Powered Legal Intelligence for India</p>
          </div>

          <div className="flex border-b border-stone-200 mb-6">
            <button
              onClick={() => setAuthMode("login")}
              className={`flex-1 py-2 text-sm font-medium ${authMode === "login" ? "text-stone-900 border-b-2 border-stone-900" : "text-stone-500"}`}
            >Sign In</button>
            <button
              onClick={() => setAuthMode("signup")}
              className={`flex-1 py-2 text-sm font-medium ${authMode === "signup" ? "text-stone-900 border-b-2 border-stone-900" : "text-stone-500"}`}
            >Create Account</button>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            {authMode === "signup" && (
              <div>
                <label className="block text-xs font-medium text-stone-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-stone-300 rounded text-sm focus:outline-none focus:border-stone-900"
                  placeholder="Your name"
                />
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-stone-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 border border-stone-300 rounded text-sm focus:outline-none focus:border-stone-900"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-700 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="w-full px-3 py-2 border border-stone-300 rounded text-sm focus:outline-none focus:border-stone-900"
                placeholder="At least 6 characters"
              />
            </div>
            {authError && (
              <div className="text-sm text-red-700 bg-red-50 p-2 rounded border border-red-200">{authError}</div>
            )}
            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-2.5 bg-stone-900 text-white text-sm font-medium rounded hover:bg-stone-800 disabled:opacity-50"
            >
              {authLoading ? "Please wait…" : authMode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-stone-900 rounded flex items-center justify-center">
              <span className="text-white font-serif font-bold text-sm">N</span>
            </div>
            <div>
              <h1 className="font-serif font-bold text-lg text-stone-900">NyayaAI</h1>
              <p className="text-[10px] text-stone-500 -mt-0.5">Legal Intelligence Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-stone-900">{user.name || user.email}</p>
              <p className="text-[10px] text-stone-500 capitalize">{user.role}</p>
            </div>
            <button
              onClick={handleLogout}
              className="text-xs text-stone-600 hover:text-stone-900 border border-stone-300 px-3 py-1.5 rounded"
            >Sign Out</button>
          </div>
        </div>
        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6 flex gap-1">
          {([
            ["documents", "Documents"],
            ["chat", "AI Assistant"],
            ["workflow", "Workflow"],
            ["drafts", "Drafts"],
          ] as [Tab, string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === key
                  ? "border-stone-900 text-stone-900"
                  : "border-transparent text-stone-500 hover:text-stone-800"
              }`}
            >{label}</button>
          ))}
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        {tab === "documents" && <DocumentsPanel />}
        {tab === "chat" && <ChatPanel />}
        {tab === "workflow" && <WorkflowPanel />}
        {tab === "drafts" && <DraftsPanel />}
      </main>

      <footer className="border-t border-stone-200 bg-white py-3 text-center text-xs text-stone-500">
        NyayaAI — Preliminary legal assistance. Always consult a qualified advocate for legal advice.
      </footer>
    </div>
  );
}

// ===== Documents Panel =====
function DocumentsPanel() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listDocuments();
      setDocs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // Poll for status updates while any doc is "processing"
    const interval = setInterval(() => {
      setDocs(prev => {
        if (prev.some(d => d.status === "processing")) {
          refresh();
        }
        return prev;
      });
    }, 3000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(file);
      await refresh();
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }, [refresh]);

  const selected = docs.find(d => d.id === selectedId);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1">
        <div className="bg-white border border-stone-200 rounded p-4">
          <h2 className="font-medium text-stone-900 mb-3">Upload Document</h2>
          <label className="block border-2 border-dashed border-stone-300 rounded p-6 text-center cursor-pointer hover:border-stone-900 transition-colors">
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
            />
            {uploading ? (
              <p className="text-sm text-stone-600">Uploading…</p>
            ) : (
              <>
                <p className="text-sm text-stone-600">Click to upload</p>
                <p className="text-xs text-stone-400 mt-1">PDF, PNG, JPG, TXT up to 20MB</p>
              </>
            )}
          </label>
        </div>

        <div className="mt-4">
          <h3 className="font-medium text-stone-900 mb-2 text-sm">Your Documents</h3>
          {loading ? (
            <p className="text-sm text-stone-500">Loading…</p>
          ) : docs.length === 0 ? (
            <p className="text-sm text-stone-500">No documents yet. Upload one to get started.</p>
          ) : (
            <div className="space-y-2">
              {docs.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setSelectedId(d.id)}
                  className={`w-full text-left p-3 border rounded text-sm ${selectedId === d.id ? "border-stone-900 bg-stone-50" : "border-stone-200 bg-white hover:border-stone-400"}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-stone-900 truncate">{d.filename}</span>
                    <StatusBadge status={d.status} />
                  </div>
                  {d.doc_type && (
                    <p className="text-xs text-stone-500 capitalize">{d.doc_type.replace(/_/g, " ")}</p>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="lg:col-span-2">
        {selected ? (
          <DocumentDetail doc={selected} onReanalyze={refresh} />
        ) : (
          <div className="bg-white border border-stone-200 rounded p-8 text-center text-stone-500">
            Select a document to view its AI analysis
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    uploaded: "bg-stone-100 text-stone-700",
    processing: "bg-amber-100 text-amber-800",
    analyzed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded ${colors[status] || colors.uploaded}`}>
      {status}
    </span>
  );
}

function DocumentDetail({ doc, onReanalyze }: { doc: DocumentItem; onReanalyze: () => void }) {
  const [section, setSection] = useState<"summary" | "explanation" | "deadlines" | "entities" | "raw">("summary");
  return (
    <div className="bg-white border border-stone-200 rounded p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="font-medium text-stone-900">{doc.filename}</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            {doc.doc_type ? doc.doc_type.replace(/_/g, " ") : "uncategorized"} ·
            {" "}{new Date(doc.created_at).toLocaleString()}
          </p>
        </div>
        <button
          onClick={() => api.reanalyze(doc.id).then(onReanalyze)}
          className="text-xs border border-stone-300 px-2 py-1 rounded hover:bg-stone-100"
        >Re-analyze</button>
      </div>

      {doc.status === "processing" && (
        <div className="bg-amber-50 border border-amber-200 p-3 rounded text-sm text-amber-900 mb-4">
          Analyzing document… this may take 20-30 seconds.
        </div>
      )}
      {doc.status === "failed" && (
        <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-900 mb-4">
          Analysis failed: {doc.error}
        </div>
      )}

      <div className="flex gap-1 mb-4 border-b border-stone-200 overflow-x-auto">
        {([
          ["summary", "Summary"],
          ["explanation", "Plain English"],
          ["deadlines", "Deadlines"],
          ["entities", "Entities"],
          ["raw", "OCR Text"],
        ] as [typeof section, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setSection(key)}
            className={`px-3 py-1.5 text-xs font-medium border-b-2 whitespace-nowrap ${
              section === key ? "border-stone-900 text-stone-900" : "border-transparent text-stone-500"
            }`}
          >{label}</button>
        ))}
      </div>

      {section === "summary" && (
        <div className="text-sm text-stone-700 leading-relaxed">{doc.summary || "No summary available yet."}</div>
      )}
      {section === "explanation" && (
        <div className="text-sm text-stone-700 leading-relaxed">{doc.plain_explanation || "No plain-language explanation available yet."}</div>
      )}
      {section === "deadlines" && (
        doc.deadlines?.length ? (
          <ul className="space-y-2">
            {doc.deadlines.map((d, i) => (
              <li key={i} className="border border-stone-200 rounded p-3 text-sm">
                <div className="font-medium text-stone-900">{d.date || "No date"}</div>
                <div className="text-stone-600 mt-1">{d.description}</div>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-stone-500">No deadlines detected.</p>
      )}
      {section === "entities" && (
        doc.key_entities?.length ? (
          <div className="space-y-2">
            {doc.key_entities.map((e, i) => (
              <div key={i} className="flex items-start gap-3 border border-stone-200 rounded p-3 text-sm">
                <span className="text-xs px-1.5 py-0.5 rounded bg-stone-100 text-stone-700 uppercase">{e.type}</span>
                <div>
                  <div className="font-medium text-stone-900">{e.label}</div>
                  <div className="text-stone-600">{e.value}</div>
                </div>
              </div>
            ))}
          </div>
        ) : <p className="text-sm text-stone-500">No key entities extracted.</p>
      )}
      {section === "raw" && (
        <pre className="text-xs text-stone-700 whitespace-pre-wrap font-mono bg-stone-50 p-3 rounded max-h-96 overflow-y-auto">
          {doc.ocr_text || "No OCR text available."}
        </pre>
      )}

      {doc.missing_info && doc.missing_info.length > 0 && (
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded text-sm">
          <p className="font-medium text-amber-900 mb-1">Missing information detected:</p>
          <ul className="list-disc list-inside text-amber-800">
            {doc.missing_info.map((m, i) => <li key={i}>{m}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

// ===== Chat Panel =====
function ChatPanel() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingChats, setLoadingChats] = useState(true);
  const [chatStatus, setChatStatus] = useState<ChatStatus | null>(null);
  const [chatStatusError, setChatStatusError] = useState<string | null>(null);

  useEffect(() => {
    api.chatStatus().then(setChatStatus).catch((e: Error) => setChatStatusError(e.message));
  }, []);

  const refreshChats = useCallback(async () => {
    setLoadingChats(true);
    try {
      const data = await api.listChats();
      setChats(data);
      if (data.length > 0 && !currentChatId) {
        setCurrentChatId(data[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingChats(false);
    }
  }, [currentChatId]);

  useEffect(() => { refreshChats(); }, []);

  useEffect(() => {
    if (!currentChatId) {
      setMessages([]);
      return;
    }
    api.getChat(currentChatId).then(c => setMessages(c.messages)).catch(console.error);
  }, [currentChatId]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || sending) return;
    const content = input.trim();
    setInput("");

    if (!currentChatId) {
      try {
        const newChat = await api.createChat("New conversation");
        setCurrentChatId(newChat.id);
        await refreshChats();
        // Now send the message
        const msg = await api.sendMessage(newChat.id, content);
        setMessages(prev => [...prev,
          { id: "tmp-user", role: "user", content, sources: [], created_at: new Date().toISOString() },
          msg,
        ]);
      } catch (e: any) {
        alert(`Failed: ${e.message}`);
      } finally {
        setSending(false);
      }
      return;
    }

    setMessages(prev => [...prev, { id: "tmp-user", role: "user", content, sources: [], created_at: new Date().toISOString() }]);
    setSending(true);
    try {
      const msg = await api.sendMessage(currentChatId, content);
      setMessages(prev => [...prev, msg]);
    } catch (e: any) {
      alert(`Failed: ${e.message}`);
    } finally {
      setSending(false);
    }
  }, [input, currentChatId, sending, refreshChats]);

  const handleNewChat = useCallback(async () => {
    try {
      const newChat = await api.createChat("New conversation");
      setCurrentChatId(newChat.id);
      setMessages([]);
      await refreshChats();
    } catch (e: any) {
      alert(`Failed: ${e.message}`);
    }
  }, [refreshChats]);

  const handleDeleteChat = useCallback(async (id: string) => {
    if (!confirm("Delete this conversation?")) return;
    try {
      await api.deleteChat(id);
      if (currentChatId === id) {
        setCurrentChatId(null);
        setMessages([]);
      }
      await refreshChats();
    } catch (e: any) {
      alert(`Failed: ${e.message}`);
    }
  }, [currentChatId, refreshChats]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100vh-200px)]">
      {/* Chat list */}
      <div className="lg:col-span-1 bg-white border border-stone-200 rounded p-3 overflow-y-auto">
        <button
          onClick={handleNewChat}
          className="w-full mb-3 py-2 bg-stone-900 text-white text-sm rounded hover:bg-stone-800"
        >+ New Conversation</button>
        {loadingChats ? (
          <p className="text-sm text-stone-500">Loading…</p>
        ) : chats.length === 0 ? (
          <p className="text-sm text-stone-500">No conversations yet.</p>
        ) : (
          <div className="space-y-1">
            {chats.map(c => (
              <div
                key={c.id}
                className={`group flex items-center justify-between px-2 py-1.5 rounded text-sm cursor-pointer ${
                  currentChatId === c.id ? "bg-stone-100" : "hover:bg-stone-50"
                }`}
                onClick={() => setCurrentChatId(c.id)}
              >
                <span className="truncate flex-1">{c.title}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteChat(c.id); }}
                  className="opacity-0 group-hover:opacity-100 text-xs text-stone-500 hover:text-red-600 ml-2"
                >×</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="lg:col-span-3 bg-white border border-stone-200 rounded flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-stone-500 mt-12">
              <p className="text-sm">Ask a legal question to get started.</p>
            </div>
          ) : messages.map(m => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] ${m.role === "user" ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-900"} rounded-lg p-3 text-sm whitespace-pre-wrap`}>
                {m.role === "assistant" && m.analysis_status && m.analysis_status !== "available" && (
                  <p className="mb-2 text-xs font-semibold text-amber-800" role="status">
                    {m.analysis_status.replaceAll("_", " ")}
                  </p>
                )}
                {m.content}
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-stone-300 space-y-2">
                    <p className="text-xs font-medium opacity-80">Official references:</p>
                    {m.sources.map((s, i) => (
                      <div key={`${s.source_id}-${s.section}-${i}`} className="text-xs bg-white/10 p-2 rounded break-words">
                        <p className="font-medium">{s.title}, section {s.section}</p>
                        <p className="opacity-70 mt-0.5">{s.law_id} · {s.jurisdiction} · reviewed {s.reviewed_at}</p>
                        {isIndiaCodeUrl(s.url) ? (
                          <a className="mt-1 inline-block underline underline-offset-2" href={s.url} target="_blank" rel="noopener noreferrer">
                            Open official source
                          </a>
                        ) : <p className="mt-1">Official source link unavailable</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {chatStatusError ? (
            <p className="mx-4 mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
              Could not check legal Q&amp;A availability: {chatStatusError}
            </p>
          ) : chatStatus ? (
            <p className={`mx-4 mt-3 rounded border p-3 text-sm ${chatStatus.analysis_status === "available" ? "border-green-200 bg-green-50 text-green-900" : "border-amber-200 bg-amber-50 text-amber-900"}`} role="status">
              Legal Q&amp;A: {chatStatus.message}
            </p>
          ) : null}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-stone-100 rounded-lg p-3 text-sm text-stone-500">
                <span className="inline-block animate-pulse">●●●</span> AI is thinking…
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-stone-200 p-3 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask a legal question…"
            className="flex-1 px-3 py-2 border border-stone-300 rounded text-sm focus:outline-none focus:border-stone-900"
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="px-4 py-2 bg-stone-900 text-white text-sm rounded hover:bg-stone-800 disabled:opacity-50"
          >Send</button>
        </div>
      </div>
    </div>
  );
}

function isIndiaCodeUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "indiacode.gov.in";
  } catch {
    return false;
  }
}

// ===== Workflow Panel =====
function WorkflowPanel() {
  const [description, setDescription] = useState("");
  const [caseTypeHint, setCaseTypeHint] = useState("");
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const w = await api.generateWorkflow({
        description: description.trim(),
        case_type_hint: caseTypeHint || undefined,
      });
      setWorkflow(w);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [description, caseTypeHint]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white border border-stone-200 rounded p-4">
        <h2 className="font-medium text-stone-900 mb-3">Describe Your Situation</h2>
        <p className="text-xs text-stone-500 mb-4">
          Tell us what happened. We&apos;ll generate a personalized step-by-step legal workflow.
        </p>
        <label className="block text-xs font-medium text-stone-700 mb-1">Case Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 border border-stone-300 rounded text-sm focus:outline-none focus:border-stone-900"
          placeholder="e.g., I received a legal notice from my landlord asking me to vacate my rented apartment in 7 days. What should I do?"
        />

        <label className="block text-xs font-medium text-stone-700 mb-1 mt-3">Case Type (optional)</label>
        <select
          value={caseTypeHint}
          onChange={(e) => setCaseTypeHint(e.target.value)}
          className="w-full px-3 py-2 border border-stone-300 rounded text-sm bg-white"
        >
          <option value="">Auto-detect</option>
          <option value="property_dispute">Property Dispute</option>
          <option value="consumer_grievance">Consumer Grievance</option>
          <option value="employment_issue">Employment Issue</option>
          <option value="family_matter">Family Matter</option>
          <option value="criminal">Criminal</option>
          <option value="tax_dispute">Tax Dispute</option>
          <option value="rti_application">RTI Application</option>
          <option value="civil_suit">Civil Suit</option>
        </select>

        {error && <p className="text-sm text-red-700 mt-3">{error}</p>}

        <button
          onClick={handleGenerate}
          disabled={loading || !description.trim()}
          className="mt-4 w-full py-2.5 bg-stone-900 text-white text-sm font-medium rounded hover:bg-stone-800 disabled:opacity-50"
        >
          {loading ? "Generating workflow…" : "Generate Workflow"}
        </button>
      </div>

      <div className="bg-white border border-stone-200 rounded p-4">
        <h2 className="font-medium text-stone-900 mb-3">Generated Workflow</h2>
        {!workflow ? (
          <p className="text-sm text-stone-500 text-center mt-12">Your personalized workflow will appear here.</p>
        ) : (
          <>
            <div className="mb-4">
              <span className="text-[10px] uppercase tracking-wider text-stone-500">Case Type</span>
              <p className="font-medium text-stone-900 capitalize">{workflow.case_type.replace(/_/g, " ")}</p>
              <p className="text-sm text-stone-600 mt-1">{workflow.summary}</p>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-stone-500">Preparation Score:</span>
                <div className="flex-1 h-2 bg-stone-200 rounded overflow-hidden">
                  <div className="h-full bg-stone-900" style={{ width: `${workflow.prep_score}%` }} />
                </div>
                <span className="text-xs font-medium">{workflow.prep_score}%</span>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <p className="text-xs font-medium text-stone-700 uppercase tracking-wider">Steps</p>
              {workflow.steps.map((s, i) => (
                <div key={i} className="border border-stone-200 rounded p-3">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-stone-900 text-white text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                      {s.step}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-stone-900 text-sm">{s.title}</p>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          s.priority === "high" ? "bg-red-100 text-red-800" :
                          s.priority === "medium" ? "bg-amber-100 text-amber-800" :
                          "bg-stone-100 text-stone-700"
                        }`}>{s.priority}</span>
                      </div>
                      <p className="text-xs text-stone-600 mt-1">{s.description}</p>
                      {s.deadline_days && (
                        <p className="text-xs text-stone-500 mt-1">⏱ Within {s.deadline_days} days</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div>
              <p className="text-xs font-medium text-stone-700 uppercase tracking-wider mb-2">Checklist</p>
              <ul className="space-y-1">
                {workflow.checklist.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-stone-700">
                    <input type="checkbox" className="mt-1" />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ===== Drafts Panel =====
function DraftsPanel() {
  const [templates, setTemplates] = useState<Record<string, DraftTemplate> | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [title, setTitle] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDraftTemplates().then(setTemplates).catch(console.error);
    api.listDrafts().then(setDrafts).catch(console.error);
  }, []);

  const handleSelectTemplate = useCallback((key: string) => {
    setSelectedTemplate(key);
    setFields({});
    setDraft(null);
    setError(null);
    if (templates && templates[key]) {
      setTitle(templates[key].label + " — " + new Date().toLocaleDateString());
    }
  }, [templates]);

  const handleGenerate = useCallback(async () => {
    if (!selectedTemplate || !templates) return;
    setLoading(true);
    setError(null);
    try {
      const newDraft = await api.createDraft(selectedTemplate, title, fields);
      setDraft(newDraft);
      const list = await api.listDrafts();
      setDrafts(list);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [selectedTemplate, title, fields, templates]);

  const handleCopy = useCallback(() => {
    if (draft) {
      navigator.clipboard.writeText(draft.content);
      alert("Draft copied to clipboard");
    }
  }, [draft]);

  const handleDownload = useCallback(() => {
    if (!draft) return;
    const blob = new Blob([draft.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${draft.draft_type}_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [draft]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Template picker + fields */}
      <div className="lg:col-span-1 bg-white border border-stone-200 rounded p-4">
        <h2 className="font-medium text-stone-900 mb-3">Choose Draft Type</h2>
        {!templates ? (
          <p className="text-sm text-stone-500">Loading templates…</p>
        ) : (
          <div className="space-y-1 mb-4">
            {Object.entries(templates).map(([key, t]) => (
              <button
                key={key}
                onClick={() => handleSelectTemplate(key)}
                className={`w-full text-left p-2 rounded border text-sm ${
                  selectedTemplate === key ? "border-stone-900 bg-stone-50" : "border-stone-200 hover:border-stone-400"
                }`}
              >
                <p className="font-medium text-stone-900">{t.label}</p>
                <p className="text-xs text-stone-500 mt-0.5">{t.description}</p>
              </button>
            ))}
          </div>
        )}

        {selectedTemplate && templates && (
          <>
            <label className="block text-xs font-medium text-stone-700 mb-1">Draft Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full mb-3 px-3 py-2 border border-stone-300 rounded text-sm"
            />

            {templates[selectedTemplate].fields.map((f) => (
              <div key={f.name} className="mb-2">
                <label className="block text-xs font-medium text-stone-700 mb-1">
                  {f.label}{f.required && <span className="text-red-600 ml-0.5">*</span>}
                </label>
                {f.textarea ? (
                  <textarea
                    value={fields[f.name] || ""}
                    onChange={(e) => setFields(prev => ({ ...prev, [f.name]: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 border border-stone-300 rounded text-sm"
                  />
                ) : (
                  <input
                    type="text"
                    value={fields[f.name] || ""}
                    onChange={(e) => setFields(prev => ({ ...prev, [f.name]: e.target.value }))}
                    className="w-full px-3 py-2 border border-stone-300 rounded text-sm"
                  />
                )}
              </div>
            ))}

            {error && <p className="text-sm text-red-700 mt-2">{error}</p>}

            <button
              onClick={handleGenerate}
              disabled={loading || !title.trim()}
              className="mt-3 w-full py-2 bg-stone-900 text-white text-sm rounded hover:bg-stone-800 disabled:opacity-50"
            >
              {loading ? "Generating…" : "Generate Draft"}
            </button>
          </>
        )}
      </div>

      {/* Draft preview */}
      <div className="lg:col-span-2 bg-white border border-stone-200 rounded p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-medium text-stone-900">Generated Draft</h2>
          {draft && (
            <div className="flex gap-2">
              <button onClick={handleCopy} className="text-xs border border-stone-300 px-2 py-1 rounded hover:bg-stone-100">Copy</button>
              <button onClick={handleDownload} className="text-xs border border-stone-300 px-2 py-1 rounded hover:bg-stone-100">Download</button>
            </div>
          )}
        </div>
        {!draft ? (
          <p className="text-sm text-stone-500 text-center mt-12">Fill in the form and click Generate Draft.</p>
        ) : (
          <pre className="text-xs text-stone-800 whitespace-pre-wrap font-mono bg-stone-50 p-3 rounded max-h-[600px] overflow-y-auto">
            {draft.content}
          </pre>
        )}

        {drafts.length > 0 && (
          <div className="mt-6">
            <h3 className="font-medium text-stone-900 mb-2 text-sm">Previous Drafts</h3>
            <div className="space-y-1">
              {drafts.map(d => (
                <button
                  key={d.id}
                  onClick={() => setDraft(d)}
                  className="w-full text-left p-2 border border-stone-200 rounded text-sm hover:border-stone-400"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-stone-900">{d.title}</span>
                    <span className="text-[10px] text-stone-500 capitalize">{d.draft_type.replace(/_/g, " ")}</span>
                  </div>
                  <p className="text-xs text-stone-500 mt-0.5">{new Date(d.created_at).toLocaleString()}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
