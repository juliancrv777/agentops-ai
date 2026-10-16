"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import "./workspace.css";

type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};
type Citation = {
  document_id: string;
  chunk_id: string;
  filename: string;
  score: number;
  excerpt: string;
};
type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
};
type Document = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
};
type Turn = {
  user_message: Message;
  assistant_message: Message;
  mode: "ai" | "extractive" | "no_evidence";
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function errorMessage(response: Response): Promise<string> {
  const parsed: unknown = await response.json().catch(() => null);
  if (parsed && typeof parsed === "object" && "detail" in parsed) {
    const detail = (parsed as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return `Request failed (${response.status})`;
}

export default function WorkspacePage() {
  const [token, setToken] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organization, setOrganization] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<string>("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const response = await fetch(`${API_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (response.ok) {
          const body = (await response.json()) as { access_token: string };
          if (mounted) setToken(body.access_token);
        }
      } catch {
        // No active session or the API is not reachable.
      } finally {
        if (mounted) setBooting(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const api = useCallback(
    async (path: string, init: RequestInit = {}): Promise<Response> => {
      const request = (access: string | null) =>
        fetch(`${API_URL}${path}`, {
          ...init,
          credentials: "include",
          headers: {
            ...(init.body && !(init.body instanceof FormData)
              ? { "Content-Type": "application/json" }
              : {}),
            ...(access ? { Authorization: `Bearer ${access}` } : {}),
            ...init.headers,
          },
        });

      let response = await request(token);
      if (response.status === 401 && token) {
        const refresh = await fetch(`${API_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!refresh.ok) {
          setToken(null);
          return response;
        }
        const body = (await refresh.json()) as { access_token: string };
        setToken(body.access_token);
        response = await request(body.access_token);
      }
      return response;
    },
    [token],
  );

  const loadLists = useCallback(async () => {
    const [chats, docs] = await Promise.all([
      api("/chat/conversations"),
      api("/documents"),
    ]);
    if (!chats.ok) throw new Error(await errorMessage(chats));
    if (!docs.ok) throw new Error(await errorMessage(docs));
    setConversations((await chats.json()) as Conversation[]);
    setDocuments((await docs.json()) as Document[]);
  }, [api]);

  useEffect(() => {
    if (!token) {
      setConversations([]);
      setDocuments([]);
      setMessages([]);
      setActiveId(null);
      return;
    }
    void loadLists().catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "Could not load workspace"),
    );
  }, [token, loadLists]);

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/auth/${registering ? "register" : "login"}`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            password,
            ...(registering ? { organization_name: organization } : {}),
          }),
        },
      );
      if (!response.ok) throw new Error(await errorMessage(response));
      const data = (await response.json()) as { access_token: string };
      setToken(data.access_token);
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setError("");
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      setToken(null);
      setNotice("");
    }
  }

  async function newConversation() {
    setError("");
    setBusy(true);
    try {
      const response = await api("/chat/conversations", {
        method: "POST",
        body: JSON.stringify({ title: "Knowledge investigation" }),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      const item = (await response.json()) as Conversation;
      setActiveId(item.id);
      setMessages([]);
      setMode("");
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create chat");
    } finally {
      setBusy(false);
    }
  }

  async function openConversation(id: string) {
    setError("");
    try {
      const response = await api(`/chat/conversations/${id}`);
      if (!response.ok) throw new Error(await errorMessage(response));
      const data = (await response.json()) as Conversation & { messages: Message[] };
      setActiveId(id);
      setMessages(data.messages);
      setMode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open chat");
    }
  }

  async function removeConversation() {
    if (!activeId || !window.confirm("Delete this conversation permanently?")) return;
    setError("");
    setBusy(true);
    try {
      const response = await api(`/chat/conversations/${activeId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      setActiveId(null);
      setMessages([]);
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete chat");
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeId || !draft.trim() || busy) return;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const response = await api(`/chat/conversations/${activeId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: draft.trim() }),
      });
      if (!response.ok) throw new Error(await errorMessage(response));
      const turn = (await response.json()) as Turn;
      setMessages((current) => [
        ...current, turn.user_message, turn.assistant_message,
      ]);
      setDraft("");
      setMode(turn.mode);
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send message");
    } finally {
      setBusy(false);
    }
  }

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fileInput = event.currentTarget.elements.namedItem("document");
    if (!(fileInput instanceof HTMLInputElement) || !fileInput.files?.[0]) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const body = new FormData();
      body.append("file", fileInput.files[0]);
      const response = await api("/documents", { method: "POST", body });
      if (!response.ok) throw new Error(await errorMessage(response));
      setNotice("Document indexed. It is now available for grounded answers.");
      fileInput.value = "";
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  if (booting) return <main className="ws-boot">Restoring secure session…</main>;

  if (!token) {
    return (
      <main className="ws-login">
        <a href="/" className="ws-back">← AgentOps AI</a>
        <section className="ws-auth">
          <div className="ws-kicker">PRIVATE KNOWLEDGE WORKSPACE</div>
          <h1>Find answers.<br /><span>Show evidence.</span></h1>
          <p>Sign in to investigate your team&apos;s uploaded documents. Conversations stay isolated to your account and organization.</p>
          <form onSubmit={authenticate} className="ws-auth-form">
            <label>Email <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></label>
            <label>Password <input type="password" minLength={registering ? 10 : 1} value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete={registering ? "new-password" : "current-password"} /></label>
            {registering && <label>Organization <input minLength={2} value={organization} onChange={(e) => setOrganization(e.target.value)} required placeholder="Acme Operations" /></label>}
            <button disabled={busy} type="submit">{busy ? "Please wait…" : registering ? "Create workspace" : "Sign in"}</button>
          </form>
          <button type="button" className="ws-text-button" onClick={() => { setRegistering(!registering); setError(""); }}>
            {registering ? "Already have an account? Sign in" : "New here? Create an account"}
          </button>
          {error && <p role="alert" className="ws-error">{error}</p>}
        </section>
      </main>
    );
  }

  return (
    <main className="ws-layout">
      <aside className="ws-sidebar">
        <a href="/" className="ws-brand"><span className="ws-brand-mark">◎</span> AGENTOPS <strong>AI</strong></a>
        <div className="ws-kicker">SECURE KNOWLEDGE</div>
        <button className="ws-new" type="button" onClick={newConversation} disabled={busy}>+ New investigation</button>
        <div className="ws-section-heading">CONVERSATIONS <span>{conversations.length}</span></div>
        <nav className="ws-conversations" aria-label="Conversations">
          {conversations.map((chat) => (
            <button key={chat.id} type="button" aria-current={activeId === chat.id ? "page" : undefined}
              className={activeId === chat.id ? "ws-chat-link active" : "ws-chat-link"}
              onClick={() => void openConversation(chat.id)}>
              <span>◷</span> <span>{chat.title}</span>
            </button>
          ))}
          {conversations.length === 0 && <p className="ws-muted">Create a conversation to get started.</p>}
        </nav>
        <div className="ws-section-heading">KNOWLEDGE FILES <span>{documents.length}</span></div>
        <form onSubmit={uploadDocument} className="ws-upload">
          <label htmlFor="doc-file">Upload a source (.txt, .md, .pdf)</label>
          <input id="doc-file" name="document" type="file" accept=".txt,.md,.pdf" required />
          <button disabled={busy} type="submit">Index document</button>
        </form>
        <ul className="ws-doc-list">
          {documents.slice(0, 10).map((doc) => <li key={doc.id} title={doc.filename}>▤ {doc.filename} <small>{doc.status}</small></li>)}
        </ul>
        <button className="ws-signout" type="button" onClick={() => void signOut()}>Sign out ↗</button>
      </aside>
      <section className="ws-main">
        <header className="ws-header">
          <div><span className="ws-kicker">KNOWLEDGE INTELLIGENCE</span><h2>Investigation workspace</h2></div>
          <div className="ws-live"><i /> Documents-backed</div>
        </header>
        {error && <div role="alert" className="ws-error">{error}</div>}
        {notice && <div role="status" className="ws-notice">{notice}</div>}
        {!activeId ? (
          <div className="ws-empty">
            <div className="ws-emblem">◎</div>
            <span className="ws-kicker">ANALYZE • VERIFY • ACT</span>
            <h3>Your operational knowledge,<br />one conversation away.</h3>
            <p>Upload a runbook or incident note, start an investigation and receive source-linked evidence.</p>
            <button className="ws-new" onClick={newConversation} disabled={busy}>Start an investigation →</button>
          </div>
        ) : (
          <>
            <div className="ws-toolbar">
              <span>INVESTIGATION / {activeId.slice(0, 8).toUpperCase()}</span>
              <button type="button" disabled={busy} onClick={() => void removeConversation()}>Delete conversation</button>
            </div>
            <div className="ws-message-list" aria-live="polite">
              {messages.length === 0 && <div className="ws-hint">Ask a question about your indexed documents. Citations will appear below the answer.</div>}
              {messages.map((message) => (
                <article key={message.id} className={message.role === "user" ? "ws-message user" : "ws-message assistant"}>
                  <div className="ws-author">{message.role === "user" ? "YOU" : "AGENTOPS • KNOWLEDGE"}</div>
                  <p>{message.content}</p>
                  {message.citations.length > 0 && <div className="ws-citations">
                    <strong>Sources</strong>
                    {message.citations.map((citation, index) => <details key={citation.chunk_id}>
                      <summary>[{index + 1}] {citation.filename} · score {citation.score.toFixed(2)}</summary>
                      <p>{citation.excerpt}</p>
                    </details>)}
                  </div>}
                </article>
              ))}
              {mode === "extractive" && <div className="ws-hint">Extractive mode: an AI chat model is not configured. Only source excerpts are displayed.</div>}
            </div>
            <form onSubmit={sendMessage} className="ws-composer">
              <label htmlFor="ws-question">ASK YOUR KNOWLEDGE BASE</label>
              <textarea id="ws-question" rows={3} maxLength={2000}
                placeholder="What does our runbook say about investigating API errors?"
                value={draft} onChange={(e) => setDraft(e.target.value)} required />
              <div><small>Grounded in your indexed documents · maximum 2,000 characters</small>
                <button type="submit" disabled={busy || draft.trim().length < 2}>
                  {busy ? "Analyzing…" : "Send question →"}
                </button>
              </div>
            </form>
          </>
        )}
      </section>
    </main>
  );
}
