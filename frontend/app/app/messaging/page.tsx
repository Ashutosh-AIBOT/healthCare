"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type Conversation = {
  id: string;
  participant_name: string;
  participant_type: "provider" | "coordinator" | "family";
  last_message: string;
  timestamp: string;
  unread: boolean;
};

type Contact = {
  id: string;
  name: string;
  type: "provider" | "coordinator" | "family";
  status: string;
};

type Message = {
  id: string;
  sender: string;
  body: string;
  timestamp: string;
  read: boolean;
};

export default function MessagingPage() {
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [contacts, setContacts] = useState<Contact[] | null>(null);
  const [messages, setMessages] = useState<Message[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [c, ct, m] = await Promise.all([
      apiClient<Conversation[]>("/api/v1/messages/conversations"),
      apiClient<Contact[]>("/api/v1/messages/contacts"),
      apiClient<Message[]>("/api/v1/messages/recent"),
    ]);
    if (c.error) {
      setError(c.error.detail || "Failed to load conversations.");
      setConversations([]);
      return;
    }
    if (ct.error) {
      setError(ct.error.detail || "Failed to load contacts.");
      setContacts([]);
      return;
    }
    if (m.error) {
      setError(m.error.detail || "Failed to load messages.");
      setMessages([]);
      return;
    }
    setConversations(c.data || []);
    setContacts(ct.data || []);
    setMessages(m.data || []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isLoading = conversations === null && contacts === null && messages === null && !error;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-10 w-32" />
          <Skeleton className="mt-2 h-5 w-72" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-[1.75rem]" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-[1.75rem]" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Messaging</h1>
        <p className="text-sm text-muted">Chat with providers, care coordinators, and family members.</p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Conversations</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{conversations?.length ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Unread</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {conversations?.filter((c) => c.unread).length ?? 0}
          </p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Providers</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {conversations?.filter((c) => c.participant_type === "provider").length ?? 0}
          </p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Family</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {conversations?.filter((c) => c.participant_type === "family").length ?? 0}
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card lg:col-span-2">
          <h2 className="font-semibold text-ink">Conversations</h2>
          {!conversations?.length ? (
            <EmptyState
              title="No conversations"
              description="Secure messaging threads will load here when connected to the messaging API."
            />
          ) : (
            <ul className="mt-4 space-y-3">
              {conversations.map((c) => (
                <li
                  key={c.id}
                  className={`flex items-center justify-between gap-4 rounded-2xl px-4 py-3 transition hover:bg-mist/60 ${
                    c.unread ? "bg-primary-soft/30" : "bg-mist/40"
                  }`}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-ink">{c.participant_name}</p>
                    <p className="truncate text-xs text-muted">{c.last_message}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-[11px] text-muted">
                      {new Date(c.timestamp).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}
                    </span>
                    {c.unread && (
                      <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground">
                        New
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <h2 className="font-semibold text-ink">Contacts</h2>
          {!contacts?.length ? (
            <p className="mt-2 text-sm text-muted">
              Providers, coordinators, and family members you can message.
            </p>
          ) : (
            <ul className="mt-4 space-y-2">
              {contacts.map((ct) => (
                <li key={ct.id} className="flex items-center justify-between rounded-2xl bg-mist/60 px-4 py-2">
                  <span className="text-sm text-ink">{ct.name}</span>
                  <span className="rounded-full bg-mist px-2.5 py-1 text-[11px] font-semibold capitalize text-muted">
                    {ct.type}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-semibold text-ink">Recent Messages</h2>
          <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
            {!messages?.length ? (
              <EmptyState
                title="No messages yet"
                description="Message threads and chat history will appear here."
              />
            ) : (
              <ul className="space-y-3">
                {messages.map((m) => (
                  <li key={m.id} className="flex items-start gap-3 border-b border-line/50 py-2 last:border-b-0">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-mist text-xs font-semibold text-ink">
                      {m.sender.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-ink">{m.sender}</p>
                        <span className="text-[11px] text-muted">
                          {new Date(m.timestamp).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}
                        </span>
                      </div>
                      <p className="mt-0.5 text-sm text-muted">{m.body}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
