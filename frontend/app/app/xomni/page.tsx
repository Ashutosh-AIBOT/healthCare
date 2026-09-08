"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  Plus, Send, ChevronRight, Menu, Mic, MicOff, Settings2,
  Utensils, Clock, Activity, FileText, Sparkles, X, Volume2, Search,
  MoreHorizontal, Link2, Download, History, BrainCircuit, ActivitySquare, TriangleAlert
} from "lucide-react";
import { apiClient, getAccessToken, setAccessToken } from "@/lib/auth-client";
import { ThemeToggle } from "@/components/theme-toggle";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Radio } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────

type Role = "user" | "assistant";

interface Message {
  id: string;
  role: Role;
  content: string;
  createdAt: Date;
  streaming?: boolean;
  action?: any;
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

// ── Voice state ─────────────────────────────────────────────────────────────

type VoiceState = "idle" | "requesting" | "recording" | "transcribing" | "error";

// ── Component ───────────────────────────────────────────────────────────────

function ProposalCard({ action, onAccept, onReject }: { action: any, onAccept: () => void, onReject: () => void }) {
  if (!action || !action.action) return null;
  const isMealPlan = action.action === "propose_meal_plan";
  const isTodo = action.action === "propose_todo";

  if (!isMealPlan && !isTodo) return null;

  return (
    <div className="mt-4 border border-primary/20 bg-primary-soft/30 rounded-xl p-4 shadow-sm w-full max-w-sm">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-4 w-4 text-primary" />
        <h4 className="text-sm font-semibold text-ink">
          {isMealPlan ? "Meal Plan Update Proposed" : "Schedule Update Proposed"}
        </h4>
      </div>

      <div className="text-[13px] text-ink/80 mb-4 bg-surface p-3 rounded-lg border border-line/50">
        {isMealPlan && action.proposal && (
          <pre className="whitespace-pre-wrap font-sans text-xs">
            {JSON.stringify(action.proposal, null, 2)}
          </pre>
        )}
        {isTodo && (
          <div>
            <p className="font-medium text-ink">{action.title}</p>
            <p className="text-muted text-xs mt-1">Time: {action.start_hour}:00 - {action.end_hour}:00</p>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Button onClick={onAccept} size="sm" className="w-full bg-primary hover:bg-primary/90 text-white shadow-sm">
          Accept
        </Button>
        <Button onClick={onReject} size="sm" variant="outline" className="w-full">
          Reject
        </Button>
      </div>
    </div>
  );
}

export default function XomniPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leftOpen, setLeftOpen] = useState(true);
  const [mode, setMode] = useState<ChatMode>("general");
  const [modeDropdown, setModeDropdown] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [ttsEnabled, setTtsEnabled] = useState(true);

  // Removed duplicate profile states

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

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



  // ── TTS helper ──────────────────────────────────────────────────────────
  const speak = (text: string) => {
    if (!ttsEnabled || typeof window === "undefined") return;
    const utt = new SpeechSynthesisUtterance(text.replace(/[*_#`]/g, "").slice(0, 500));
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
                  if (payload.conversation_id && payload.conversation_id !== activeConvId) {
                    setActiveConvId(payload.conversation_id);
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
    [loading, mode, activeConvId, ttsEnabled]
  );

  // ── Voice recording ──────────────────────────────────────────────────────
  const startVoiceRecording = async () => {
    setVoiceError(null);
    setVoiceState("requesting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/ogg";

      const recorder = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setVoiceState("transcribing");

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");

        const token = getAccessToken();
        try {
          const res = await fetch("/api/v1/xomni/voice/transcribe", {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            credentials: "include",
            body: formData,
          });

          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Transcription failed" }));
            throw new Error(err.detail || "Transcription failed");
          }

          const data = await res.json() as { transcript: string };
          if (data.transcript.trim()) {
            setInput(data.transcript);
            await send(data.transcript);
          } else {
            setVoiceError("Could not understand audio. Please try again.");
          }
        } catch (e) {
          setVoiceError(e instanceof Error ? e.message : "Voice failed. Check API key.");
        } finally {
          setVoiceState("idle");
        }
      };

      recorder.start(250);
      mediaRecorderRef.current = recorder;
      setVoiceState("recording");
    } catch (e) {
      setVoiceState("error");
      setVoiceError("Microphone access denied. Please allow microphone permissions.");
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleVoice = () => {
    if (voiceState === "recording") {
      stopVoiceRecording();
    } else if (voiceState === "idle") {
      void startVoiceRecording();
    }
  };

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
            <div className="h-6 w-6 bg-gradient-to-br from-primary to-violet-600 rounded-md flex items-center justify-center text-white text-[10px] font-bold shadow-sm">
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
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleVoice}
              className={cn(
                "hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-lg shadow-sm transition-all",
                voiceState === "recording" ? "bg-rose-500 text-white animate-pulse" : "bg-primary text-primary-foreground hover:bg-primary-hover"
              )}
            >
              <Radio className={cn("h-3.5 w-3.5", voiceState === "recording" ? "animate-ping" : "animate-pulse")} />
              {voiceState === "recording" ? "Listening..." : "Voice Talk"}
            </button>
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
                <div className="h-24 w-24 rounded-full bg-gradient-to-br from-violet-300 via-primary/50 to-rose-200 blur-xl opacity-60 absolute top-1/4 -translate-y-1/2" />
                <div className="relative z-10 h-16 w-16 rounded-full bg-gradient-to-br from-white to-primary-soft shadow-lg shadow-primary/10 flex items-center justify-center mb-6 border border-white/50">
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
                        <div className="h-8 w-8 shrink-0 rounded-full bg-gradient-to-br from-accent-teal to-accent-water flex items-center justify-center shadow-card ring-1 ring-border">
                          <Sparkles className="h-4 w-4 text-white" />
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
                            <div className="prose prose-sm max-w-none prose-p:my-2 prose-headings:mt-4 prose-headings:mb-2 prose-headings:font-display prose-headings:text-ink prose-a:text-primary">
                              {message.content ? message.content.split("\n").map((line, i) => {
                                const bold = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
                                return (
                                  <p
                                    key={i}
                                    className={line.startsWith("- ") ? "ml-4" : ""}
                                    dangerouslySetInnerHTML={{ __html: bold || "&nbsp;" }}
                                  />
                                );
                              }) : null}
                              {message.streaming && (
                                <div className={cn("flex items-center", message.content ? "mt-2" : "mt-0")}>
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-primary/15 to-violet-500/15 border border-primary/20 shadow-[0_0_15px_rgba(var(--primary),0.15)] relative overflow-hidden">
                                    <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-[shimmer_2s_infinite] -skew-x-12" />
                                    <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary),0.8)] animate-bounce" style={{ animationDuration: "800ms" }} />
                                    <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary),0.8)] animate-bounce" style={{ animationDelay: "150ms", animationDuration: "800ms" }} />
                                    <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary),0.8)] animate-bounce" style={{ animationDelay: "300ms", animationDuration: "800ms" }} />
                                  </span>
                                </div>
                              )}
                            </div>
                          ) : (
                            <p className="whitespace-pre-wrap">{message.content}</p>
                          )}
                          {message.action && message.role === "assistant" && !message.streaming && (
                            <ProposalCard
                              action={message.action}
                              onAccept={async () => {
                                try {
                                  const token = getAccessToken();
                                  if (message.action.action === "propose_meal_plan") {
                                    await fetch("/api/v1/nutrition/meal-plan/save", {
                                      method: "POST",
                                      headers: {
                                        "Content-Type": "application/json",
                                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                                      },
                                      body: JSON.stringify({
                                        plan_json: message.action.proposal,
                                        created_by: "XOMNI"
                                      }),
                                    });
                                  } else if (message.action.action === "propose_todo") {
                                    await fetch("/api/v1/time/todos", {
                                      method: "POST",
                                      headers: {
                                        "Content-Type": "application/json",
                                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                                      },
                                      body: JSON.stringify({
                                        title: message.action.title,
                                        due_date: new Date().toISOString().split("T")[0],
                                        priority: message.action.priority || "normal",
                                        created_by: "XOMNI"
                                      }),
                                    });
                                  }
                                  // Add a system response back to chat
                                  setMessages(prev => [...prev, {
                                    id: `${Date.now()}-sys`,
                                    role: "user",
                                    content: "I have accepted this proposal.",
                                    createdAt: new Date()
                                  }]);
                                } catch (e) {
                                  console.error(e);
                                }
                              }}
                              onReject={() => {
                                setMessages(prev => [...prev, {
                                  id: `${Date.now()}-sys`,
                                  role: "user",
                                  content: "I reject this proposal. Let's adjust it.",
                                  createdAt: new Date()
                                }]);
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
              {(voiceError || voiceState === "recording" || voiceState === "transcribing") && (
                <div className="flex justify-center mb-3">
                  <div className={cn(
                    "text-[11px] rounded-full px-4 py-1.5 flex items-center gap-2 shadow-sm font-medium backdrop-blur",
                    voiceState === "recording" ? "bg-rose-500/90 text-white animate-pulse" :
                      voiceState === "transcribing" ? "bg-amber-100/90 text-amber-800 border border-amber-200" :
                        "bg-critical/90 text-white"
                  )}>
                    {voiceState === "recording" && <><Mic className="h-3 w-3" /> Recording… tap mic to stop</>}
                    {voiceState === "transcribing" && <><span className="h-3 w-3 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" /> Transcribing…</>}
                    {voiceError && voiceError}
                  </div>
                </div>
              )}

              <div className={cn(
                "bg-surface border border-border shadow-sm rounded-[1.25rem] p-1.5 flex items-end gap-1 sm:gap-2 relative focus-within:ring-2 focus-within:ring-primary focus-within:border-primary transition-all",
                voiceState === "recording" && "ring-2 ring-rose-500/30 border-rose-500/50 shadow-[0_0_20px_rgba(244,63,94,0.15)]"
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
                  <button
                    onClick={toggleVoice}
                    className={cn(
                      "h-10 w-10 shrink-0 rounded-full flex items-center justify-center transition-all",
                      voiceState === "recording"
                        ? "bg-rose-500 text-white shadow-[0_0_15px_rgba(244,63,94,0.4)] animate-pulse"
                        : "bg-primary/10 text-primary hover:bg-primary/20"
                    )}
                    title={voiceState === "recording" ? "Stop Voice Talk" : "Start Voice Talk"}
                  >
                    {voiceState === "recording" ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                  </button>

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

