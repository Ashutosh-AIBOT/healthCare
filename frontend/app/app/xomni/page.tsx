"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  Plus, Send, ChevronRight, Menu, Mic, MicOff, Settings2,
  Utensils, Clock, Activity, FileText, Sparkles, X, Volume2,
} from "lucide-react";
import { getAccessToken } from "@/lib/auth-client";

// ── Types ──────────────────────────────────────────────────────────────────

type Role = "user" | "assistant";

interface Message {
  id: string;
  role: Role;
  content: string;
  createdAt: Date;
  streaming?: boolean;
}

interface Conversation {
  id: string;
  title: string;
  mode: string;
  updated_at: string;
}

type ChatMode = "general" | "food" | "timetable" | "reports" | "fitness";

const MODE_META: Record<ChatMode, { label: string; icon: React.ReactNode; color: string; prompt: string }> = {
  general:   { label: "General",    icon: <Sparkles className="h-4 w-4" />, color: "text-primary",  prompt: "Ask me anything…" },
  food:      { label: "Food & Nutrition", icon: <Utensils className="h-4 w-4" />, color: "text-emerald-600", prompt: "Ask about food, nutrition, BMI…" },
  timetable: { label: "Timetable",  icon: <Clock className="h-4 w-4" />,    color: "text-amber-600", prompt: "Add a task, plan your day…" },
  fitness:   { label: "Fitness",    icon: <Activity className="h-4 w-4" />, color: "text-blue-600",  prompt: "Ask about workouts, fitness goals…" },
  reports:   { label: "Reports",    icon: <FileText className="h-4 w-4" />, color: "text-violet-600", prompt: "Ask about your lab report values…" },
};

const QUICK_PROMPTS: Record<ChatMode, string[]> = {
  general:   ["What should I eat today?", "How much water should I drink?", "Tips for better sleep"],
  food:      ["How much protein do I need daily?", "Best veg protein sources", "What fruits are high in iron?", "Suggest a 1500 cal diet plan"],
  timetable: ["Add gym session at 7am", "Schedule study at 9-11am", "What's my most productive time?"],
  fitness:   ["Best workout for weight loss", "How to build muscle fast", "Pre-workout meal ideas"],
  reports:   ["Explain my cholesterol values", "What does low hemoglobin mean?", "Is my blood sugar normal?"],
};

// ── Voice state ─────────────────────────────────────────────────────────────

type VoiceState = "idle" | "requesting" | "recording" | "transcribing" | "error";

// ── Component ───────────────────────────────────────────────────────────────

export default function XomniPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rightOpen, setRightOpen] = useState(true);
  const [mode, setMode] = useState<ChatMode>("food");
  const [promptOpen, setPromptOpen] = useState(false);
  const [userPromptPrefix, setUserPromptPrefix] = useState("");
  const [promptDraft, setPromptDraft] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [ttsEnabled, setTtsEnabled] = useState(true);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // ── Scroll to bottom ────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Load conversation history on mount ──────────────────────────────────
  useEffect(() => {
    void loadConversations();
    // Start with welcome message
    setMessages([{
      id: "welcome",
      role: "assistant",
      content: "Hi! I'm **Xomni** — your food, fitness and health AI. I can talk about any food (veg or non-veg), calculate your nutrition needs, plan meals, and help manage your schedule.\n\nTry switching modes above or pick a quick prompt below. 🌱",
      createdAt: new Date(),
    }]);
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
            user_prompt_prefix: userPromptPrefix || null,
            stream: true,
          }),
        });

        if (!res.ok) {
          const txt = await res.text();
          throw new Error(txt || `Error ${res.status}`);
        }

        // Handle SSE stream
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

          for (const line of lines) {
            if (line.startsWith("event: meta")) continue;
            if (line.startsWith("event: done")) {
              // Conversation ID from meta
            }
            if (line.startsWith("data: ")) {
              try {
                const payload = JSON.parse(line.slice(6));
                if (payload.token) {
                  fullText += payload.token;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId ? { ...m, content: fullText } : m
                    )
                  );
                }
                if (payload.conversation_id) {
                  setActiveConvId(payload.conversation_id);
                }
              } catch { /* ignore parse errors */ }
            }
          }
        }

        // Finalize (stop streaming indicator)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m
          )
        );

        // TTS for assistant response
        if (fullText) speak(fullText);

        // Reload conversation list
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
    [loading, mode, activeConvId, userPromptPrefix, ttsEnabled]
  );

  // ── Voice recording (Groq Whisper STT) ─────────────────────────────────
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
            // Auto-send after voice transcription
            await send(data.transcript);
          } else {
            setVoiceError("Could not understand audio. Please try again.");
          }
        } catch (e) {
          setVoiceError(e instanceof Error ? e.message : "Voice failed. Add Groq API key in Profile.");
        } finally {
          setVoiceState("idle");
        }
      };

      recorder.start(250); // collect chunks every 250ms
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
    setMessages([{
      id: "welcome",
      role: "assistant",
      content: "New conversation started. What would you like to talk about?",
      createdAt: new Date(),
    }]);
  };

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-paper">

      {/* ── Center chat area ────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col min-w-0">

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-line/50 bg-surface/80 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-violet-600 text-white text-sm font-bold shadow">
              X
            </div>
            <div>
              <h1 className="font-display text-sm font-semibold text-ink leading-none">Xomni</h1>
              <p className="text-[11px] text-muted mt-0.5">
                NVIDIA Nemotron · Groq Whisper · {ttsEnabled ? "Voice On" : "Voice Off"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setTtsEnabled((v) => !v)}
              title={ttsEnabled ? "Mute voice" : "Enable voice"}
              className={cn(
                "p-2 rounded-xl transition-colors",
                ttsEnabled ? "text-primary bg-primary-soft" : "text-muted hover:bg-mist"
              )}
            >
              <Volume2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => { setPromptDraft(userPromptPrefix); setPromptOpen(true); }}
              title="Set your preferences"
              className="p-2 rounded-xl text-muted hover:bg-mist hover:text-ink transition-colors"
            >
              <Settings2 className="h-4 w-4" />
            </button>
            <button onClick={startNewChat} className="p-2 rounded-xl text-muted hover:bg-mist hover:text-ink transition-colors">
              <Plus className="h-4 w-4" />
            </button>
            <button onClick={() => setRightOpen((v) => !v)} className="p-2 rounded-xl text-muted hover:bg-mist hover:text-ink transition-colors">
              {rightOpen ? <ChevronRight className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Mode selector */}
        <div className="flex gap-1.5 px-4 py-2 border-b border-line/30 bg-surface/60 overflow-x-auto no-scrollbar">
          {(Object.keys(MODE_META) as ChatMode[]).map((m) => {
            const meta = MODE_META[m];
            return (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={cn(
                  "flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all",
                  mode === m
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted hover:bg-mist hover:text-ink"
                )}
              >
                <span className={mode === m ? "text-primary-foreground" : meta.color}>
                  {meta.icon}
                </span>
                {meta.label}
              </button>
            );
          })}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 no-scrollbar">
          <div className="mx-auto max-w-3xl space-y-5">

            {/* Quick prompts (only when 1 message) */}
            {messages.length <= 1 && (
              <div className="mt-2 space-y-3">
                <p className="text-xs font-medium text-muted text-center">Quick prompts for {MODE_META[mode].label}</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {QUICK_PROMPTS[mode].map((q) => (
                    <button
                      key={q}
                      onClick={() => void send(q)}
                      className="rounded-2xl border border-line bg-surface px-4 py-2 text-sm text-ink hover:bg-mist hover:border-primary/40 transition-all"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message bubbles */}
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 text-sm leading-relaxed",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.role === "assistant" && (
                  <span className="mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-violet-600 text-xs font-bold text-white shadow-sm">
                    X
                  </span>
                )}
                <div
                  className={cn(
                    "max-w-[82%] rounded-2xl px-4 py-3",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground rounded-tr-md"
                      : "bg-mist text-ink rounded-tl-md"
                  )}
                >
                  {message.role === "assistant" ? (
                    <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:mt-2">
                      {/* Simple markdown-like rendering */}
                      {message.content.split("\n").map((line, i) => {
                        const bold = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
                        return (
                          <p
                            key={i}
                            className={line.startsWith("- ") ? "ml-3" : ""}
                            dangerouslySetInnerHTML={{ __html: bold || "&nbsp;" }}
                          />
                        );
                      })}
                      {message.streaming && (
                        <span className="inline-flex items-center gap-1 ml-1">
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDuration: "700ms" }} />
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "140ms", animationDuration: "700ms" }} />
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "280ms", animationDuration: "700ms" }} />
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  )}
                </div>
              </div>
            ))}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="border-t border-line/50 bg-surface/90 backdrop-blur px-4 py-3">
          <div className="mx-auto max-w-3xl space-y-2">
            {error && (
              <p className="text-xs text-critical bg-critical/5 rounded-xl px-3 py-1.5">{error}</p>
            )}
            {(voiceError || voiceState === "recording" || voiceState === "transcribing") && (
              <div className={cn(
                "text-xs rounded-xl px-3 py-1.5 flex items-center gap-2",
                voiceState === "recording" ? "bg-rose-50 text-rose-700 animate-pulse" :
                voiceState === "transcribing" ? "bg-amber-50 text-amber-700" :
                "bg-critical/5 text-critical"
              )}>
                {voiceState === "recording" && <><Mic className="h-3 w-3" /> Recording… tap again to stop</>}
                {voiceState === "transcribing" && <><span className="h-3 w-3 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" /> Transcribing with Groq Whisper…</>}
                {voiceError && voiceError}
              </div>
            )}

            <div className="flex items-end gap-2">
              {/* Voice button */}
              <button
                onClick={toggleVoice}
                disabled={voiceState === "transcribing" || voiceState === "requesting"}
                title="Voice input (Groq Whisper)"
                className={cn(
                  "flex-shrink-0 h-11 w-11 flex items-center justify-center rounded-2xl transition-all",
                  voiceState === "recording"
                    ? "bg-rose-500 text-white animate-pulse shadow-lg shadow-rose-200"
                    : voiceState === "transcribing"
                    ? "bg-amber-100 text-amber-700 cursor-not-allowed"
                    : "bg-mist text-muted hover:bg-primary-soft hover:text-primary"
                )}
              >
                {voiceState === "recording" ? (
                  <MicOff className="h-5 w-5" />
                ) : voiceState === "transcribing" ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
                ) : (
                  <Mic className="h-5 w-5" />
                )}
              </button>

              {/* Text input */}
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={MODE_META[mode].prompt}
                className="flex-1 rounded-2xl border-line bg-surface px-4 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/10"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send(input);
                  }
                }}
              />

              {/* Send button */}
              <Button
                onClick={() => void send(input)}
                disabled={!input.trim() || loading}
                className="h-11 w-11 rounded-2xl p-0 flex-shrink-0"
              >
                {loading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-[10px] text-muted/60 text-center">
              Chat: NVIDIA Nemotron · Stream: Groq LLaMA-3.3 · Voice: Groq Whisper
            </p>
          </div>
        </div>
      </div>

      {/* ── Right sidebar (conversations) ───────────────────────────────── */}
      <aside
        className={cn(
          "flex flex-col border-l border-line bg-surface transition-all duration-300 ease-out overflow-hidden",
          rightOpen ? "w-72" : "w-0"
        )}
      >
        <div className="px-4 py-3 border-b border-line flex items-center justify-between shrink-0">
          <h2 className="font-semibold text-sm text-ink">Conversations</h2>
          <span className="text-xs text-muted bg-mist rounded-lg px-2 py-0.5">{conversations.length}</span>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <p className="text-xs text-muted px-3 py-4 text-center">Your conversations will appear here.</p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => void loadConversation(conv.id)}
                className={cn(
                  "w-full text-left rounded-xl px-3 py-2.5 transition-colors group",
                  activeConvId === conv.id ? "bg-primary-soft" : "hover:bg-mist"
                )}
              >
                <div className="flex items-start justify-between gap-1">
                  <p className={cn(
                    "text-xs font-medium truncate leading-snug",
                    activeConvId === conv.id ? "text-primary" : "text-ink"
                  )}>
                    {conv.title}
                  </p>
                  <span className={cn(
                    "text-[10px] shrink-0 rounded-lg px-1.5 py-0.5 mt-0.5",
                    MODE_META[conv.mode as ChatMode]?.color || "text-muted",
                    "bg-mist/80"
                  )}>
                    {conv.mode}
                  </span>
                </div>
                <p className="text-[10px] text-muted mt-0.5">
                  {new Date(conv.updated_at).toLocaleDateString()}
                </p>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* ── Prompt preferences modal ─────────────────────────────────────── */}
      {promptOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-surface rounded-3xl shadow-lift p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-ink">Your Preferences</h2>
              <button onClick={() => setPromptOpen(false)} className="text-muted hover:text-ink">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-muted mb-3">
              Tell Xomni about your dietary restrictions, dislikes, allergies, or preferences.
              This is sent with every message.
            </p>
            <textarea
              value={promptDraft}
              onChange={(e) => setPromptDraft(e.target.value)}
              placeholder="E.g. I'm vegetarian, allergic to nuts, don't like bitter foods, prefer low-carb meals..."
              rows={5}
              className="w-full rounded-2xl border border-line bg-paper px-4 py-3 text-sm outline-none resize-none focus:border-primary focus:ring-2 focus:ring-primary/10"
            />
            <div className="flex gap-2 mt-4 justify-end">
              <Button variant="outline" onClick={() => setPromptOpen(false)}>Cancel</Button>
              <Button onClick={() => {
                setUserPromptPrefix(promptDraft);
                setPromptOpen(false);
              }}>
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
