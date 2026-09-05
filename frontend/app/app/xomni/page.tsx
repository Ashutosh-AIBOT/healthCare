"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: Date;
};

const SUGGESTIONS = [
  "Explain my last hemoglobin result in plain language.",
  "Which preventive checkups fit my family profile?",
  "Summarize my appointment history this month.",
  "Compare my last two lab reports for trends.",
];

export default function XomniPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi, I’m Xomni. I can explain reports, track trends, and help you prepare for appointments. What would you like to do first?",
      createdAt: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const send = useCallback(
    async (content: string) => {
      if (!content.trim()) return;
      const userMessage: Message = {
        id: `${Date.now()}-user`,
        role: "user",
        content,
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setLoading(true);
      setError(null);

      try {
        const token = typeof window !== "undefined" ? sessionStorage.getItem("aarogya_access") : null;
        const res = await fetch("/api/v1/ai/ask", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          credentials: "include",
          body: JSON.stringify({
            question: content,
            member_id: null,
            document_id: null,
          }),
        });

        if (!res.body) {
          throw new Error("No response from assistant.");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        let full = "";

        const assistantId = `${Date.now()}-assistant`;
        setMessages((prev) => [
          ...prev,
          {
            id: assistantId,
            role: "assistant",
            content: "",
            createdAt: new Date(),
          },
        ]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const parts = buf.split("\n");
          buf = parts.pop() || "";
          for (const line of parts) {
            if (line.startsWith("data:")) {
              const chunk = line.slice(5).trimStart();
              if (chunk) {
                full += chunk;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: full }
                      : m,
                  ),
                );
              }
            }
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return (
    <div className="flex h-[calc(100dvh-8rem)] flex-col">
      <div className="mb-4">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Xomni</h1>
        <p className="mt-1 text-sm text-muted">
          Your health assistant. Ask about reports, appointments, or next steps.
        </p>
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden p-0">
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 text-sm leading-relaxed",
                  message.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                {message.role === "assistant" ? (
                  <span className="mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-mist text-xs font-semibold text-ink">
                    X
                  </span>
                ) : null}
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-4 py-3",
                    message.role === "user"
                      ? "bg-primary-soft text-ink"
                      : "bg-surface shadow-card",
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="border-t border-line px-6 py-4">
          <div className="mx-auto max-w-3xl">
            {error ? (
              <p className="mb-2 text-xs text-critical">{error}</p>
            ) : null}
            <div className="flex items-end gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Xomni anything about your health..."
                rows={1}
                className="min-h-[44px] flex-1 rounded-2xl border border-line bg-surface px-4 py-3 text-sm outline-none transition-colors duration-300 ease-soft placeholder:text-muted/70 focus:border-primary focus:ring-2 focus:ring-ink/10"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send(input);
                  }
                }}
              />
              <Button size="md" loading={loading} onClick={() => void send(input)} disabled={!input.trim()}>
                Send
              </Button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void send(s)}
                  className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs text-muted transition-colors duration-300 ease-soft hover:bg-mist hover:text-ink"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
