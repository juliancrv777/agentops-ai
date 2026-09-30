"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import styles from "./workspace-client.module.css";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

type Profile = {
  user_id: string;
  email: string;
  display_name: string | null;
  organization_id: string;
  role: string;
};

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
  metadata: Record<string, unknown>;
};

type Message = {
  id: string;
  role: string;
  content: string;
  citations: Citation[];
  created_at: string;
};

type DocumentItem = {
  id: string;
  filename: string;
  mime_type: string | null;
  size_bytes: number | null;
  status: string;
  created_at: string;
};

type StreamEvent =
  | { event: "sources"; data: { citations: Citation[] } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: { message_id: string; citations: Citation[] } }
  | { event: "error"; data: { message: string } };

function parseEventBlock(block: string): StreamEvent | null {
  let eventName = "";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!eventName || dataLines.length === 0) {
    return null;
  }

  try {
    return {
      event: eventName,
      data: JSON.parse(dataLines.join("\n")) as unknown,
    } as StreamEvent;
  } catch {
    return null;
  }
}

function formatBytes(value: number | null): string {
  if (!value) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export default function WorkspaceClient() {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(
    null,
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [question, setQuestion] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isRestoring, setIsRestoring] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const selected = useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.id === selectedConversation,
      ) ?? null,
    [conversations, selectedConversation],
  );

  async function refreshToken(): Promise<string | null> {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) return null;

    const payload = (await response.json()) as AuthResponse;
    setAccessToken(payload.access_token);
    return payload.access_token;
  }

  async function authedFetch(
    path: string,
    options: RequestInit = {},
    tokenOverride?: string,
  ): Promise<Response> {
    let token = tokenOverride ?? accessToken;

    if (!token) {
      token = await refreshToken();
    }

    if (!token) {
      throw new Error("Authentication required.");
    }

    const headers = new Headers(options.headers);
    headers.set("Authorization", `Bearer ${token}`);

    let response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
    });

    if (response.status === 401) {
      const refreshed = await refreshToken();
      if (!refreshed) return response;

      headers.set("Authorization", `Bearer ${refreshed}`);
      response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
        credentials: "include",
      });
    }

    return response;
  }

  async function loadMessages(conversationId: string, token?: string) {
    const response = await authedFetch(
      `/chat/conversations/${conversationId}/messages`,
      {},
      token,
    );

    if (response.ok) {
      setMessages((await response.json()) as Message[]);
    }
  }

  async function loadWorkspace(token: string) {
    const [profileResponse, conversationResponse, documentResponse] =
      await Promise.all([
        authedFetch("/auth/me", {}, token),
        authedFetch("/chat/conversations", {}, token),
        authedFetch("/documents", {}, token),
      ]);

    if (!profileResponse.ok) {
      throw new Error("Could not restore the authenticated session.");
    }

    setProfile((await profileResponse.json()) as Profile);

    if (conversationResponse.ok) {
      const list = (await conversationResponse.json()) as Conversation[];
      setConversations(list);

      if (list.length > 0) {
        setSelectedConversation((current) => current ?? list[0].id);
        if (!selectedConversation) {
          await loadMessages(list[0].id, token);
        }
      }
    }

    if (documentResponse.ok) {
      setDocuments((await documentResponse.json()) as DocumentItem[]);
    }
  }

  useEffect(() => {
    let active = true;

    async function restore() {
      try {
        const token = await refreshToken();
        if (token && active) {
          await loadWorkspace(token);
        }
      } catch {
        if (active) setNotice("Session restoration failed.");
      } finally {
        if (active) setIsRestoring(false);
      }
    }

    void restore();

    return () => {
      active = false;
    };
    // Session restoration runs once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);

    const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
    const body =
      authMode === "login"
        ? { email, password }
        : {
            email,
            password,
            organization_name: organizationName,
          };

    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as
        | { detail?: string }
        | null;
      setNotice(payload?.detail ?? "Authentication failed.");
      return;
    }

    const payload = (await response.json()) as AuthResponse;
    setAccessToken(payload.access_token);
    await loadWorkspace(payload.access_token);
  }

  async function logout() {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });

    setAccessToken(null);
    setProfile(null);
    setConversations([]);
    setDocuments([]);
    setMessages([]);
    setSelectedConversation(null);
    setStreamingText("");
    setStreamingCitations([]);
  }

  async function createConversation(): Promise<string | null> {
    const response = await authedFetch("/chat/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      setNotice("Could not create a conversation.");
      return null;
    }

    const conversation = (await response.json()) as Conversation;
    setConversations((current) => [conversation, ...current]);
    setSelectedConversation(conversation.id);
    setMessages([]);
    return conversation.id;
  }

  async function chooseConversation(id: string) {
    setSelectedConversation(id);
    setStreamingText("");
    setStreamingCitations([]);
    await loadMessages(id);
  }

  async function uploadDocument(file: File | null) {
    if (!file) return;

    setIsUploading(true);
    setNotice(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await authedFetch("/documents", {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        setNotice(payload?.detail ?? "Document upload failed.");
        return;
      }

      const document = (await response.json()) as DocumentItem;
      setDocuments((current) => [
        document,
        ...current.filter((item) => item.id !== document.id),
      ]);
      setNotice(`${document.filename} is ready for retrieval.`);
    } finally {
      setIsUploading(false);
    }
  }

  async function sendQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = question.trim();
    if (!content || isStreaming) return;

    let conversationId = selectedConversation;
    if (!conversationId) {
      conversationId = await createConversation();
    }

    if (!conversationId) return;

    setQuestion("");
    setStreamingText("");
    setStreamingCitations([]);
    setIsStreaming(true);
    setNotice(null);

    try {
      const response = await authedFetch(
        `/chat/conversations/${conversationId}/messages/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
        },
      );

      if (!response.ok || !response.body) {
        setNotice("The chat request could not be started.");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });

        let boundary = buffer.indexOf("\n\n");
        while (boundary >= 0) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const parsed = parseEventBlock(block);

          if (parsed?.event === "sources") {
            setStreamingCitations(parsed.data.citations ?? []);
          } else if (parsed?.event === "token") {
            setStreamingText((current) => current + parsed.data.text);
          } else if (parsed?.event === "error") {
            setNotice(parsed.data.message);
          }

          boundary = buffer.indexOf("\n\n");
        }

        if (done) break;
      }

      await loadMessages(conversationId);

      const conversationResponse = await authedFetch("/chat/conversations");
      if (conversationResponse.ok) {
        setConversations(
          (await conversationResponse.json()) as Conversation[],
        );
      }

      setStreamingText("");
      setStreamingCitations([]);
    } catch {
      setNotice("The streaming connection was interrupted.");
    } finally {
      setIsStreaming(false);
    }
  }

  if (isRestoring) {
    return (
      <main className={styles.centered}>
        <div className={styles.loader} />
        <p>Restoring secure workspace…</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className={styles.authShell}>
        <section className={styles.authIntro}>
          <a href="/" className={styles.brand}>
            AgentOps AI
          </a>
          <span className={styles.kicker}>SECURE KNOWLEDGE WORKSPACE</span>
          <h1>Ground answers in your own operational knowledge.</h1>
          <p>
            Upload internal documents, retrieve tenant-isolated context, and
            stream grounded answers with source metadata.
          </p>
        </section>

        <section className={styles.authCard}>
          <div className={styles.authTabs}>
            <button
              type="button"
              className={authMode === "login" ? styles.activeTab : ""}
              onClick={() => setAuthMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              className={authMode === "register" ? styles.activeTab : ""}
              onClick={() => setAuthMode("register")}
            >
              Create workspace
            </button>
          </div>

          <form onSubmit={submitAuth} className={styles.form}>
            {authMode === "register" && (
              <label>
                Organization
                <input
                  required
                  minLength={2}
                  value={organizationName}
                  onChange={(event) => setOrganizationName(event.target.value)}
                  placeholder="Acme Operations"
                />
              </label>
            )}

            <label>
              Email
              <input
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
              />
            </label>

            <label>
              Password
              <input
                required
                minLength={authMode === "register" ? 10 : 1}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••••"
              />
            </label>

            {notice && <p className={styles.notice}>{notice}</p>}

            <button className={styles.primaryButton} type="submit">
              {authMode === "login" ? "Sign in" : "Create secure workspace"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.workspace}>
      <aside className={styles.sidebar}>
        <div>
          <a href="/" className={styles.brand}>
            AgentOps AI
          </a>
          <p className={styles.userMeta}>
            {profile.email}
            <span>{profile.role}</span>
          </p>
        </div>

        <button
          type="button"
          className={styles.newChat}
          onClick={() => void createConversation()}
        >
          + New conversation
        </button>

        <div className={styles.sideSection}>
          <div className={styles.sectionHeading}>
            <span>Conversations</span>
            <span>{conversations.length}</span>
          </div>
          <div className={styles.conversationList}>
            {conversations.map((conversation) => (
              <button
                type="button"
                key={conversation.id}
                className={
                  conversation.id === selectedConversation
                    ? styles.selectedConversation
                    : styles.conversationButton
                }
                onClick={() => void chooseConversation(conversation.id)}
              >
                {conversation.title}
              </button>
            ))}
            {conversations.length === 0 && (
              <p className={styles.emptySmall}>No conversations yet.</p>
            )}
          </div>
        </div>

        <div className={styles.sideSection}>
          <div className={styles.sectionHeading}>
            <span>Knowledge</span>
            <span>{documents.length}</span>
          </div>

          <label className={styles.uploadButton}>
            {isUploading ? "Processing…" : "+ Add document"}
            <input
              type="file"
              accept=".txt,.md,.pdf"
              disabled={isUploading}
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                void uploadDocument(file);
                event.target.value = "";
              }}
            />
          </label>

          <div className={styles.documentList}>
            {documents.map((document) => (
              <div className={styles.documentRow} key={document.id}>
                <span>{document.filename}</span>
                <small>
                  {document.status} · {formatBytes(document.size_bytes)}
                </small>
              </div>
            ))}
          </div>
        </div>

        <button type="button" className={styles.logoutButton} onClick={logout}>
          Sign out
        </button>
      </aside>

      <section className={styles.chatPanel}>
        <header className={styles.chatHeader}>
          <div>
            <span className={styles.kicker}>GROUNDED CHAT</span>
            <h2>{selected?.title ?? "New conversation"}</h2>
          </div>
          <div className={styles.statusPill}>
            <span />
            Retrieval online
          </div>
        </header>

        {notice && (
          <div className={styles.workspaceNotice} role="status">
            {notice}
          </div>
        )}

        <div className={styles.messages}>
          {messages.length === 0 && !streamingText && (
            <div className={styles.emptyState}>
              <span className={styles.kicker}>READY</span>
              <h3>Ask about the documents in this workspace.</h3>
              <p>
                Answers are retrieved within your organization boundary and
                carry structured source citations.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <article
              key={message.id}
              className={
                message.role === "user"
                  ? styles.userMessage
                  : styles.assistantMessage
              }
            >
              <span className={styles.messageRole}>
                {message.role === "user" ? "You" : "AgentOps"}
              </span>
              <p>{message.content}</p>
              {message.citations.length > 0 && (
                <div className={styles.citations}>
                  {message.citations.map((citation) => (
                    <span key={citation.chunk_id}>
                      {citation.filename} · {(citation.score * 100).toFixed(0)}%
                    </span>
                  ))}
                </div>
              )}
            </article>
          ))}

          {isStreaming && (
            <article className={styles.assistantMessage}>
              <span className={styles.messageRole}>AgentOps · streaming</span>
              <p>{streamingText || "Retrieving grounded context…"}</p>
              {streamingCitations.length > 0 && (
                <div className={styles.citations}>
                  {streamingCitations.map((citation) => (
                    <span key={citation.chunk_id}>{citation.filename}</span>
                  ))}
                </div>
              )}
            </article>
          )}
        </div>

        <form className={styles.composer} onSubmit={sendQuestion}>
          <textarea
            value={question}
            disabled={isStreaming}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question about your knowledge base…"
            rows={3}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <div className={styles.composerFooter}>
            <span>Enter to send · Shift+Enter for a new line</span>
            <button
              type="submit"
              disabled={isStreaming || !question.trim()}
              className={styles.sendButton}
            >
              {isStreaming ? "Streaming…" : "Send"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
