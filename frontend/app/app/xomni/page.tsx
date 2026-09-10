"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  Plus, Send, ChevronRight, Menu, Settings2,
  Utensils, Clock, Activity, FileText, Sparkles, X, Volume2, Search,
  MoreHorizontal, Link2, Download, History, BrainCircuit, ActivitySquare, TriangleAlert
} from "lucide-react";
import { apiClient, getAccessToken, setAccessToken } from "@/lib/auth-client";
import { VoiceTalkButton } from "@/components/app/voice-talk-button";
import { MarkdownMessage } from "@/components/app/markdown-message";
import { ThemeToggle } from "@/components/theme-toggle";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

// ── Types ──────────────────────────────────────────────────────────────────

type Role = "user" | "assistant";

interface Citation {
  source: string;
  label: string;
  page?: number | null;
}

interface Message {
  id: string;
  role: Role;
  content: string;
  createdAt: Date;
  streaming?: boolean;
  action?: any;
  citations?: Citation[];
}

interface Conversation {
  id: string;
  title: string;
  mode: string;
  updated_at: string;
}

type Me = {
  full_name: string | null;
  handle: string | null;
  email: string;
  role: string;
};

type ChatMode = "general" | "food" | "timetable" | "reports" | "fitness";

function formatActionHour(value: unknown) {
  const minutes = Math.round(Number(value) * 60);
  if (!Number.isFinite(minutes) || minutes < 0 || minutes > 1440) return "unspecified";
  const hour = Math.floor(minutes / 60);
  const minute = String(minutes % 60).padStart(2, "0");
  return `${String(hour % 24 || 24).padStart(2, "0")}:${minute}`;
}

const MODE_META: Record<ChatMode, { label: string; icon: React.ReactNode; color: string; prompt: string }> = {
  general: { label: "General", icon: <Sparkles className="h-4 w-4" />, color: "text-text-primary", prompt: "Ask me anything..." },
  food: { label: "Food", icon: <Utensils className="h-4 w-4" />, color: "text-accent-teal", prompt: "Ask about food & nutrition..." },
  timetable: { label: "Timetable", icon: <Clock className="h-4 w-4" />, color: "text-accent-gold", prompt: "Plan your day..." },
  fitness: { label: "Fitness", icon: <Activity className="h-4 w-4" />, color: "text-accent-water", prompt: "Ask about workouts..." },
  reports: { label: "Reports", icon: <FileText className="h-4 w-4" />, color: "text-danger", prompt: "Ask about lab reports..." },
};

const QUICK_PROMPTS: Record<ChatMode, Array<{ title: string, desc: string }>> = {
  general: [
    { title: "Synthesize Data", desc: "Turn my meeting notes into 5 key bullet points." },
    { title: "Creative Brainstorm", desc: "Generate 3 taglines for a new brand." },
    { title: "Check Facts", desc: "Compare key differences between diets." }
  ],
  food: [
    { title: "Protein Needs", desc: "How much protein do I need daily?" },
    { title: "Veg Sources", desc: "Best vegetarian protein sources." },
    { title: "Diet Plan", desc: "Suggest a 1500 cal diet plan." }
  ],
  timetable: [
    { title: "Morning Routine", desc: "Add gym session at 7am." },
    { title: "Focus Blocks", desc: "Schedule study at 9-11am." },
    { title: "Optimization", desc: "What's my most productive time?" }
  ],
  fitness: [
    { title: "Weight Loss", desc: "Best workout for weight loss." },
    { title: "Muscle Gain", desc: "How to build muscle fast." },
    { title: "Nutrition", desc: "Pre-workout meal ideas." }
  ],
  reports: [
    { title: "Cholesterol", desc: "Explain my cholesterol values." },
    { title: "Hemoglobin", desc: "What does low hemoglobin mean?" },
    { title: "Blood Sugar", desc: "Is my blood sugar normal?" }
  ],
};

// ── Component ───────────────────────────────────────────────────────────────

import { ProposalCard, type ConfirmResult } from "@/components/app/proposal-card";

export default function XomniPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const contextMemberId = searchParams.get("member_id");
  const contextDocumentId = searchParams.get("document_id");
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leftOpen, setLeftOpen] = useState(true);
  const [mode, setMode] = useState<ChatMode>("general");
  const [modeDropdown, setModeDropdown] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);

  // Removed duplicate profile states

  const bottomRef = useRef<HTMLDivElement | null>(null);

  // ── Scroll to bottom ────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Load conversation history & user data on mount ────────────────────────
  useEffect(() => {
    let cancelled = false;
    void loadConversations();



    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const requestedMode = searchParams.get("mode") as ChatMode | null;
    if (requestedMode && requestedMode in MODE_META) setMode(requestedMode);
  }, [searchParams]);

  const loadConversations = async () => {
    const token = getAccessToken();
    try {
      const res = await fetch("/api/v1/xomni/conversations", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json() as Conversation[];
        setConversations(data);
      }
    } catch { /* silent */ }
  };



  // ── TTS helper (spoken reply = short summary; full text stays on screen) ──
  // Muted while the LiveKit room is active so the browser voice never talks
  // over the realtime agent voice (single-audio calls).
  const [voiceRoomActive, setVoiceRoomActive] = useState(false);
  const speak = (text: string) => {
    if (!ttsEnabled || voiceRoomActive || typeof window === "undefined") return;
    const clean = text.replace(/[*_#`]/g, "");
    const sentences = clean.match(/[^.!?]+[.!?]+/g) ?? [clean];
    const summary = sentences.slice(0, 2).join(" ").trim().slice(0, 500);
    if (!summary) return;
    const utt = new SpeechSynthesisUtterance(summary);
    utt.rate = 1.05;
    utt.pitch = 1.0;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utt);
  };

  // ── SSE streaming send ──────────────────────────────────────────────────
  const send = useCallback(
    async (content: string) => {
      if (!content.trim() || loading) return;

      const userMsg: Message = {
        id: `${Date.now()}-user`,
        role: "user",
        content,
        createdAt: new Date(),
      };
      const assistantId = `${Date.now()}-assistant`;
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date(),
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setLoading(true);
      setError(null);

      const token = getAccessToken();
      let fullText = "";

      try {
        const res = await fetch("/api/v1/xomni/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          credentials: "include",
          body: JSON.stringify({
            message: content,
            mode,
            conversation_id: activeConvId,
            member_id: contextMemberId || undefined,
            document_id: contextDocumentId || undefined,
            stream: true,
          }),
        });

        if (!res.ok) {
          const txt = await res.text();
          throw new Error(txt || `Error ${res.status}`);
        }

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) throw new Error("No response stream");

        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          let currentEvent = "message";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
              continue;
            }
            if (line.startsWith("data: ")) {
              try {
                const payload = JSON.parse(line.slice(6));

                if (currentEvent === "meta") {
                  if (payload.action) {
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantId ? { ...m, action: payload.action } : m
                      )
                    );
                  }
                  if (Array.isArray(payload.citations) && payload.citations.length) {
                    const cites: Citation[] = payload.citations
                      .filter((c: any) => c && typeof c.label === "string")
                      .map((c: any) => ({
                        source: String(c.source ?? "record"),
                        label: String(c.label).slice(0, 80),
                        page: typeof c.page === "number" ? c.page : null,
                      }));
                    if (cites.length) {
                      setMessages((prev) =>
                        prev.map((m) =>
                          m.id === assistantId ? { ...m, citations: cites } : m
                        )
                      );
                    }
                  }
                  if (payload.conversation_id && payload.conversation_id !== activeConvId) {
                    setActiveConvId(payload.conversation_id);
                  }
                  if (payload.citations) {
                    setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, citations: payload.citations } : m));
                  }
                  if (payload.applied) {
                    window.dispatchEvent(new CustomEvent("aarogya:data-changed", {
                      detail: { source: "xomni", action: "confirmed", applied: payload.applied },
                    }));
                  }
                } else {
                  if (payload.token) {
                    fullText += payload.token;
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantId ? { ...m, content: fullText } : m
                      )
                    );
                  }
                }
              } catch { /* ignore parse errors */ }
            }
          }
        }

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m
          )
        );

        if (fullText) speak(fullText);
        void loadConversations();
      } catch (e) {
        const errMsg = e instanceof Error ? e.message : "Something went wrong.";
        setError(errMsg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `❌ ${errMsg}`, streaming: false }
              : m
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [loading, mode, activeConvId, contextMemberId, contextDocumentId, ttsEnabled, voiceRoomActive]
  );

  // ── Live voice-room transcript → same send path as typed input ──────────
  const handleVoiceRoomTranscript = useCallback(
    (text: string) => {
      void send(text);
    },
    [send]
  );

  // ── Load conversation messages ──────────────────────────────────────────
  const loadConversation = async (convId: string) => {
    setActiveConvId(convId);
    const token = getAccessToken();
    try {
      const res = await fetch(`/api/v1/xomni/conversations/${convId}/messages`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json() as Array<{ id: string; role: string; content: string; created_at: string }>;
        setMessages(data.map((m) => ({
          id: m.id,
          role: m.role as Role,
          content: m.content,
          createdAt: new Date(m.created_at),
        })));
      }
    } catch { /* silent */ }
  };

  const startNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
  };

  const isEmpty = messages.length === 0;

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-1 w-full overflow-hidden bg-paper">

      {/* ── Left Sidebar (History & Nav) ───────────────────────── */}
      <aside
        className={cn(
          "flex-shrink-0 flex flex-col border-r border-line/40 bg-surface transition-all duration-300 ease-out z-10",
          leftOpen ? "w-64 sm:w-72" : "w-0 hidden md:flex md:w-0"
        )}
      >
        {/* Brand & New Chat */}
        <div className="p-4 space-y-4 shrink-0">
          <div className="flex items-center gap-2 px-1">
            <div className="h-6 w-6 rounded-md bg-primary-soft text-primary flex items-center justify-center text-[10px] font-bold shadow-sm">
              X
            </div>
            <h2 className="font-semibold text-ink text-[15px] tracking-tight">Xomni</h2>
          </div>

          <Button
            onClick={startNewChat}
            className="w-full justify-start gap-2 bg-ink text-paper hover:bg-ink/90 rounded-xl h-11 shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New chat
          </Button>

        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-1 no-scrollbar mt-2">
          <div className="px-3 pb-2">
            <p className="text-[11px] font-semibold text-muted/60 uppercase tracking-wider">Today</p>
          </div>
          {conversations.length === 0 ? (
            <p className="text-[13px] text-muted px-4 py-2">No history yet.</p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => void loadConversation(conv.id)}
                className={cn(
                  "w-full text-left rounded-xl px-3 py-2 transition-colors group flex flex-col gap-0.5",
                  activeConvId === conv.id ? "bg-mist/60 text-ink" : "text-muted hover:bg-mist/30 hover:text-ink"
                )}
              >
                <p className="text-[13px] truncate font-medium">{conv.title}</p>
              </button>
            ))
          )}
        </div>


      </aside>

      {/* ── Main Chat Area ────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col relative min-w-0 bg-paper">

        {/* Header - seamlessly integrated */}
        <header className="h-16 shrink-0 flex items-center justify-between px-6 z-20 bg-surface/50 backdrop-blur border-b border-line/30">
          <div className="flex items-center gap-2">
            <button onClick={() => setLeftOpen(!leftOpen)} className="md:hidden p-2 -ml-2 rounded-xl text-muted hover:bg-mist">
              <Menu className="h-5 w-5" />
            </button>

            {/* Mode Dropdown */}
            <div className="relative">
              <button
                onClick={() => setModeDropdown(!modeDropdown)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-surface-hover transition-colors text-[13px] font-medium text-text-primary"
              >
                <div className={cn("h-4 w-4 rounded-full flex items-center justify-center", MODE_META[mode].color, "bg-surface-hover")}>
                  {MODE_META[mode].icon}
                </div>
                Xomni {MODE_META[mode].label}
                <ChevronRight className={cn("h-3 w-3 text-text-secondary transition-transform", modeDropdown && "rotate-90")} />
              </button>

              {modeDropdown && (
                <div className="absolute top-full left-0 mt-1 w-48 bg-surface border border-line rounded-xl shadow-lift py-1 z-50">
                  {(Object.keys(MODE_META) as ChatMode[]).map((m) => (
                    <button
                      key={m}
                      onClick={() => { setMode(m); setModeDropdown(false); }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-ink hover:bg-mist transition-colors"
                    >
                      <span className={MODE_META[m].color}>{MODE_META[m].icon}</span>
                      {MODE_META[m].label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {(contextMemberId || contextDocumentId) && (
              <span className="hidden sm:inline-flex items-center gap-1 rounded-lg bg-danger/10 px-2 py-1 text-[11px] font-medium text-danger">
                <FileText className="h-3 w-3" /> Report context attached
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setTtsEnabled(!ttsEnabled)}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-ink text-paper text-[12px] font-medium rounded-lg hover:bg-ink/90 transition-colors"
            >
              {ttsEnabled ? <Volume2 className="h-3.5 w-3.5" /> : <MicOff className="h-3.5 w-3.5" />}
              {ttsEnabled ? "Voice On" : "Voice Off"}
            </button>
            <div className="h-6 w-px bg-line/60 mx-1 hidden sm:block" />
            <ThemeToggle className="rounded-xl p-2 text-muted hover:bg-mist hover:text-ink" />


          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 flex flex-col relative min-w-0 bg-paper overflow-hidden">

          <div className="flex-1 overflow-y-auto no-scrollbar relative flex flex-col">
            {isEmpty ? (
              // ── EMPTY STATE (Cortex Style) ──
              <div className="flex-1 flex flex-col items-center justify-center px-4 md:px-8 pb-12 w-full max-w-4xl mx-auto">
                {/* Center Orb/Logo */}
                <div className="relative z-10 h-16 w-16 rounded-xl bg-primary-soft flex items-center justify-center mb-6 border border-primary/20">
                  <Sparkles className="h-6 w-6 text-primary" />
                </div>

                <h1 className="text-2xl sm:text-3xl font-display font-medium text-primary text-center mb-1">
                  Hello there
                </h1>
                <h2 className="text-3xl sm:text-4xl font-display font-semibold text-ink text-center mb-8 tracking-tight">
                  How can I assist you today?
                </h2>
              </div>
            ) : (
              // ── ACTIVE CHAT STATE ──
              <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full px-4 pt-6 pb-6">
                <div className="space-y-6">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={cn(
                        "flex gap-4",
                        message.role === "user" ? "justify-end" : "justify-start"
                      )}
                    >
                      {message.role === "assistant" && (
                        <div className="h-8 w-8 shrink-0 rounded-lg bg-primary-soft text-primary flex items-center justify-center shadow-card ring-1 ring-border">
                          <Sparkles className="h-4 w-4" />
                        </div>
                      )}
                      <div
                        className={cn(
                          "max-w-[85%] sm:max-w-[80%]",
                          message.role === "user" ? "items-end" : "items-start"
                        )}
                      >
                        <div className={cn(
                          "px-5 py-3.5 text-[14px] leading-relaxed",
                          message.role === "user"
                            ? "bg-mist rounded-[1.5rem] text-ink"
                            : "bg-transparent text-ink"
                        )}>
                          {message.role === "assistant" ? (
                            <div>
                              {message.content ? <MarkdownMessage content={message.content} /> : null}
                              {message.streaming && (
                                <div className={cn("flex items-center", message.content ? "mt-2" : "mt-0")}>
                                  <span className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary-soft/60 px-3 py-1.5">
                                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse [animation-delay:150ms]" />
                                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse [animation-delay:300ms]" />
                                  </span>
                                </div>
                              )}
                              {!message.streaming && message.citations && message.citations.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-1.5 border-t border-line/40 pt-2 text-[10px] text-muted">
                                  <span className="font-semibold">Sources:</span>
                                  {message.citations.slice(0, 6).map((citation, index) => <span key={`${citation.source}-${citation.label}-${index}`} className="rounded-full bg-mist px-2 py-0.5">{citation.label}{citation.page ? ` · p.${citation.page}` : ""}</span>)}
                                </div>
                              )}
                            </div>
                          ) : (
                            <p className="whitespace-pre-wrap">{message.content}</p>
                          )}
                          {message.role === "assistant" &&
                            !message.streaming &&
                            message.citations &&
                            message.citations.length > 0 && (
                              <div className="flex flex-wrap gap-1.5 mt-2 pl-1" aria-label="Sources">
                                {message.citations.slice(0, 8).map((cite, i) => (
                                  <span
                                    key={`${cite.source}-${i}`}
                                    title={`${cite.source}${cite.page ? ` · page ${cite.page}` : ""}`}
                                    className="inline-flex items-center gap-1 rounded-full border border-line/60 bg-mist/40 px-2.5 py-1 text-[11px] font-medium text-muted"
                                  >
                                    <Link2 className="h-3 w-3" />
                                    {cite.label}
                                    {cite.page ? ` · p${cite.page}` : ""}
                                  </span>
                                ))}
                              </div>
                            )}
                          {message.action && message.role === "assistant" && !message.streaming && (
                            <ProposalCard
                              action={message.action}
                              onAccept={async (edited) => {
                                const token = getAccessToken();
                                if (!activeConvId) throw new Error("This proposal is no longer attached to a conversation.");
                                const response = await fetch("/api/v1/xomni/actions/confirm", {
                                  method: "POST",
                                  headers: {
                                    "Content-Type": "application/json",
                                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                                  },
                                  credentials: "include",
                                  body: JSON.stringify({ conversation_id: activeConvId, edited_action: edited }),
                                });
                                if (!response.ok) throw new Error((await response.text()) || "Could not apply proposal.");
                                const result = (await response.json()) as ConfirmResult;
                                await loadConversation(activeConvId);
                                await loadConversations();
                                window.dispatchEvent(new CustomEvent("aarogya:data-changed", {
                                  detail: { source: "xomni", action: "confirmed" },
                                }));
                                return result;
                              }}
                              onReject={async () => {
                                if (activeConvId) {
                                  const token = getAccessToken();
                                  await fetch("/api/v1/xomni/actions/reject", {
                                    method: "POST",
                                    headers: {
                                      "Content-Type": "application/json",
                                      ...(token ? { Authorization: `Bearer ${token}` } : {}),
                                    },
                                    credentials: "include",
                                    body: JSON.stringify({ conversation_id: activeConvId }),
                                  });
                                }
                              }}
                            />
                          )}
                        </div>
                        {message.role === "assistant" && (
                          <div className="flex items-center gap-2 mt-2 pl-2">
                            <button className="text-[11px] font-medium text-muted hover:text-ink transition-colors">Copy</button>
                            <span className="text-muted/30">•</span>
                            <button className="text-[11px] font-medium text-muted hover:text-ink transition-colors">Retry</button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {error && (
                    <div className="flex items-center justify-between rounded-xl border border-danger/30 bg-danger/5 p-4 mx-4">
                      <div className="flex items-center gap-3">
                        <TriangleAlert className="h-5 w-5 text-danger" />
                        <p className="text-[13px] font-medium text-danger">{error}</p>
                      </div>
                      <button onClick={() => setError(null)} className="rounded-lg px-3 py-1.5 text-[13px] font-medium text-danger hover:bg-danger/10 transition-colors">
                        Dismiss
                      </button>
                    </div>
                  )}
                  <div ref={bottomRef} className="h-4" />
                </div>
              </div>
            )}
          </div>

          {/* Unified Input Box (Docked statically at bottom) */}
          <div className="shrink-0 w-full bg-paper px-4 pb-6 pt-2 z-30">
            <div className="max-w-3xl mx-auto relative">
              <div className={cn(
                "bg-surface border border-border shadow-sm rounded-[1.25rem] p-1.5 flex items-end gap-1 sm:gap-2 relative focus-within:ring-2 focus-within:ring-primary focus-within:border-primary transition-all"
              )}>
                <button className="h-10 w-10 shrink-0 rounded-full flex items-center justify-center text-muted hover:bg-mist hover:text-ink transition-colors mb-0.5" title="Attach file">
                  <Link2 className="h-4 w-4" />
                </button>

                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask me anything..."
                  className="flex-1 bg-transparent border-none shadow-none px-2 py-3 text-[14px] outline-none min-h-[44px] max-h-32 resize-none placeholder:text-muted/60"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void send(input);
                    }
                  }}
                />

                <div className="flex items-center gap-1 mb-0.5 pr-1">
                  <VoiceTalkButton
                    onTranscript={handleVoiceRoomTranscript}
                    onError={handleVoiceRoomError}
                    context={mode}
                    onActiveChange={setVoiceRoomActive}
                  />

                  <Button
                    onClick={() => void send(input)}
                    disabled={!input.trim() || loading}
                    className="h-10 w-10 shrink-0 rounded-full p-0 bg-ink hover:bg-ink/80 text-paper transition-transform active:scale-95 disabled:opacity-50"
                  >
                    {loading ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

    </div>
  );
}
