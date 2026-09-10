"use client";

import { useCallback, useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient, getAccessToken, setAccessToken } from "@/lib/auth-client";
import { Eye, EyeOff, CheckCircle2, AlertCircle, ExternalLink } from "lucide-react";
import Link from "next/link";

type UserProfile = {
  id: string;
  email: string;
  full_name: string | null;
  handle: string | null;
  ai_context: string | null;
  role: string;
  is_verified: boolean;
  totp_enabled: boolean;
  created_at: string;
};

type ApiKeyItem = {
  id: string;
  provider: string;
  is_active: boolean;
  created_at: string;
};

type NutritionProfile = {
  bmi: number | null;
  bmr_calories: number | null;
  tdee_calories: number | null;
  target_protein_g: number | null;
  target_carbs_g: number | null;
  target_fat_g: number | null;
  goal: string | null;
  diet_type: string | null;
  activity_level: string | null;
  height_cm: number | null;
  weight_kg: number | null;
};

// ── Provider key config ───────────────────────────────────────────────────
const AI_PROVIDERS = [
  {
    id: "nvidia",
    label: "NVIDIA NIM",
    subtitle: "Primary chat LLM (Nemotron-3.5)",
    placeholder: "nvapi-...",
    docsUrl: "https://build.nvidia.com/",
    color: "text-emerald-600",
    badge: "Chat",
    badgeColor: "bg-emerald-100 text-emerald-700",
  },
  {
    id: "groq",
    label: "Groq",
    subtitle: "Streaming + Whisper STT (voice input)",
    placeholder: "gsk_...",
    docsUrl: "https://console.groq.com/keys",
    color: "text-accent-water",
    badge: "Voice + Stream",
    badgeColor: "bg-accent-water/15 text-accent-water",
  },
  {
    id: "openai",
    label: "OpenAI",
    subtitle: "Fallback LLM (GPT-4o-mini)",
    placeholder: "sk-...",
    docsUrl: "https://platform.openai.com/api-keys",
    color: "text-accent-water",
    badge: "Fallback",
    badgeColor: "bg-accent-water/15 text-accent-water",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    subtitle: "Fallback LLM (Gemini 1.5 Flash)",
    placeholder: "AIza...",
    docsUrl: "https://aistudio.google.com/app/apikey",
    color: "text-accent-teal",
    badge: "Fallback",
    badgeColor: "bg-accent-teal/15 text-accent-teal",
  },
];

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[] | null>(null);
  const [nutritionProfile, setNutritionProfile] = useState<NutritionProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editHandle, setEditHandle] = useState("");
  const [editAiContext, setEditAiContext] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const token = getAccessToken();
    if (!token) { setError("Please log in again."); return; }
    const [me, keys, nut] = await Promise.all([
      apiClient<UserProfile>("/api/v1/auth/me"),
      apiClient<ApiKeyItem[]>("/api/v1/profile/api-keys"),
      apiClient<NutritionProfile>("/api/v1/nutrition/profile"),
    ]);
    if (me.error || !me.data) { setError(me.error?.detail || "Failed to load profile."); return; }
    setProfile(me.data);
    setEditName(me.data.full_name || "");
    setEditHandle(me.data.handle || "");
    setEditAiContext(me.data.ai_context || "");
    setApiKeys(keys.data || []);
    if (nut.data) setNutritionProfile(nut.data);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const saveProfile = async () => {
    setSaving(true);
    setSaveMsg(null);
    const res = await apiClient("/api/v1/profile/me", {
      method: "PUT",
      body: JSON.stringify({ full_name: editName, handle: editHandle, ai_context: editAiContext }),
    });
    setSaving(false);
    if (res.error) setSaveMsg(`Error: ${res.error.detail}`);
    else { setSaveMsg("Saved!"); void load(); }
  };

  const isLoading = profile === null && apiKeys === null && !error;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-[1.75rem]" />)}
        </div>
        <Skeleton className="h-64 rounded-[1.75rem]" />
      </div>
    );
  }

  const keysByProvider = Object.fromEntries((apiKeys || []).map((k) => [k.provider, k]));

  return (
    <div className="space-y-8 pb-12">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Profile</h1>
        <p className="mt-1 text-sm text-muted">Manage your account, AI keys, and integrations.</p>
      </div>

      {error && (
        <div className="rounded-2xl bg-critical/5 border border-critical/20 px-4 py-3 text-sm text-critical flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />{error}
        </div>
      )}

      {/* ── Stats ── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Member Since", value: profile?.created_at ? new Date(profile.created_at).getFullYear() : "—" },
          { label: "AI Keys", value: apiKeys?.filter((k) => k.is_active).length ?? 0 },
          { label: "Verified", value: profile?.is_verified ? "✓" : "✗" },
          { label: "2FA", value: profile?.totp_enabled ? "On" : "Off" },
        ].map((s) => (
          <div key={s.label} className="rounded-[1.75rem] bg-surface p-6 shadow-card">
            <p className="text-xs text-muted">{s.label}</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{s.value}</p>
          </div>
        ))}
      </div>

      {/* ── Account details ── */}
      <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
        <h2 className="font-semibold text-ink mb-4">Account Details</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-xs text-muted">Full Name</label>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} className="mt-1" placeholder="Your name" />
          </div>
          <div>
            <label className="text-xs text-muted">Handle</label>
            <Input value={editHandle} onChange={(e) => setEditHandle(e.target.value)} className="mt-1" placeholder="@handle" />
          </div>
          <div>
            <label className="text-xs text-muted">Email</label>
            <p className="mt-1 text-sm font-medium text-ink">{profile?.email}</p>
          </div>
          <div>
            <label className="text-xs text-muted">Role</label>
            <p className="mt-1 text-sm font-medium text-ink capitalize">{profile?.role}</p>
          </div>
        </div>

        <div className="mt-6 border-t border-line/40 pt-6">
          <label className="text-xs text-muted mb-1 block">Global AI Context</label>
          <p className="text-[11px] text-muted/80 mb-3">
            Tell Xomni about your dietary restrictions, dislikes, allergies, or fitness goals. This context powers every response automatically.
          </p>
          <textarea
            value={editAiContext}
            onChange={(e) => setEditAiContext(e.target.value)}
            placeholder="E.g. I'm vegetarian, allergic to nuts, trying to build muscle..."
            rows={3}
            className="w-full rounded-2xl border border-line bg-mist/30 px-4 py-3 text-[14px] outline-none resize-none focus:border-primary/40 focus:bg-surface focus:ring-4 focus:ring-primary/10 transition-all placeholder:text-muted/60"
          />
        </div>

        <div className="mt-4 flex items-center gap-3">
          <Button onClick={saveProfile} loading={saving} disabled={saving}>Save Changes</Button>
          {saveMsg && <p className="text-sm text-healthy">{saveMsg}</p>}
        </div>
      </div>

      {/* ── Metabolic & Health Stats Card ── */}
      <div className="rounded-[1.75rem] bg-surface p-6 shadow-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-ink">Metabolic & Health Stats</h2>
            <p className="text-xs text-muted">Your calculated clinical baselines and macronutrient targets</p>
          </div>
          <Link
            href="/app/food"
            className="text-xs font-semibold text-primary hover:underline"
          >
            Manage Diet Plan →
          </Link>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 pt-1">
          <div className="rounded-2xl border border-line bg-mist/20 p-4">
            <span className="text-[11px] font-semibold text-muted uppercase">BMI Score</span>
            <p className="mt-1 text-2xl font-bold text-ink">{nutritionProfile?.bmi ?? 22.8}</p>
            <p className="text-[11px] text-emerald-600 font-medium">Normal weight</p>
          </div>
          <div className="rounded-2xl border border-line bg-mist/20 p-4">
            <span className="text-[11px] font-semibold text-muted uppercase">Daily TDEE</span>
            <p className="mt-1 text-2xl font-bold text-ink">{nutritionProfile?.tdee_calories ?? 2150} <span className="text-xs font-normal text-muted">kcal</span></p>
            <p className="text-[11px] text-muted">BMR: {nutritionProfile?.bmr_calories ?? 1650} kcal</p>
          </div>
          <div className="rounded-2xl border border-line bg-mist/20 p-4">
            <span className="text-[11px] font-semibold text-muted uppercase">Protein Target</span>
            <p className="mt-1 text-2xl font-bold text-ink">{nutritionProfile?.target_protein_g ?? 120} <span className="text-xs font-normal text-muted">g/day</span></p>
            <p className="text-[11px] text-muted">Goal: {nutritionProfile?.goal?.replace("_", " ") ?? "maintain"}</p>
          </div>
          <div className="rounded-2xl border border-line bg-mist/20 p-4">
            <span className="text-[11px] font-semibold text-muted uppercase">Diet Type</span>
            <p className="mt-1 text-2xl font-bold text-ink capitalize">{nutritionProfile?.diet_type ?? "Balanced"}</p>
            <p className="text-[11px] text-muted capitalize">{nutritionProfile?.activity_level?.replace("_", " ") ?? "Moderately active"}</p>
          </div>
        </div>
      </div>

      {/* ── AI Provider Keys ── */}
      <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-semibold text-ink">AI Provider Keys</h2>
          <span className="text-xs text-muted">Stored encrypted · never logged</span>
        </div>
        <p className="text-xs text-muted mb-6">
          <strong>NVIDIA</strong> powers Xomni chat. <strong>Groq</strong> enables voice (Whisper STT) and fast streaming responses.
        </p>
        <div className="space-y-4">
          {AI_PROVIDERS.map((provider) => {
            const existing = keysByProvider[provider.id];
            return (
              <ProviderKeyRow
                key={provider.id}
                provider={provider}
                existing={existing}
                onSaved={() => void load()}
              />
            );
          })}
        </div>
      </div>

      {/* ── LiveKit ── */}
      <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-semibold text-ink">LiveKit Voice Sessions</h2>
          <a href="https://cloud.livekit.io" target="_blank" rel="noopener" className="text-xs text-primary flex items-center gap-1 hover:underline">
            Get credentials <ExternalLink className="h-3 w-3" />
          </a>
        </div>
        <p className="text-xs text-muted mb-4">
          LiveKit enables WebRTC audio capture for Xomni voice input. Set credentials in your server's <code>.env</code> file:
          <code className="ml-1 bg-mist rounded px-1.5 py-0.5 text-[11px]">LIVEKIT_URL</code>
          <code className="ml-1 bg-mist rounded px-1.5 py-0.5 text-[11px]">LIVEKIT_API_KEY</code>
          <code className="ml-1 bg-mist rounded px-1.5 py-0.5 text-[11px]">LIVEKIT_API_SECRET</code>
        </p>
        <div className="rounded-2xl bg-mist/60 p-4 text-xs text-muted space-y-1">
          <p>• Free tier: 10,000 minutes/month on LiveKit Cloud</p>
          <p>• Or run locally: <code className="bg-surface px-1 rounded">docker run -p 7880:7880 livekit/livekit-server --dev</code></p>
          <p>• Voice also works without LiveKit using browser's built-in MediaRecorder API</p>
        </div>
      </div>

      {/* ── Telegram Integration ── */}
      <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-semibold text-ink">Telegram Integration</h2>
          <a href="https://t.me/BotFather" target="_blank" rel="noopener" className="text-xs text-primary flex items-center gap-1 hover:underline">
            Create Bot <ExternalLink className="h-3 w-3" />
          </a>
        </div>
        <p className="text-xs text-muted mb-4">
          Connect Xomni to Telegram. Message your bot and get AI responses. Chat history is saved automatically.
        </p>
        <TelegramKeyForm existing={keysByProvider["telegram"]} onSaved={() => void load()} />
      </div>
    </div>
  );
}

// ── ProviderKeyRow component ──────────────────────────────────────────────
function ProviderKeyRow({
  provider,
  existing,
  onSaved,
}: {
  provider: typeof AI_PROVIDERS[number];
  existing?: ApiKeyItem;
  onSaved: () => void;
}) {
  const [key, setKey] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    if (!key.trim()) return;
    setSaving(true);
    setErr(null);
    setMsg(null);
    const res = await apiClient<{ id: string }>("/api/v1/profile/api-keys/upsert", {
      method: "POST",
      body: JSON.stringify({ provider: provider.id, api_key: key }),
    });
    setSaving(false);
    if (res.error) setErr(res.error.detail || "Failed to save.");
    else { setMsg("Saved!"); setKey(""); onSaved(); }
  };

  return (
    <div className="rounded-2xl border border-line bg-mist/30 p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-ink">{provider.label}</p>
            <span className={`text-[10px] rounded-full px-2 py-0.5 font-medium ${provider.badgeColor}`}>
              {provider.badge}
            </span>
          </div>
          <p className="text-xs text-muted mt-0.5">{provider.subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          {existing?.is_active ? (
            <span className="flex items-center gap-1 text-xs text-healthy">
              <CheckCircle2 className="h-3.5 w-3.5" /> Active
            </span>
          ) : (
            <span className="text-xs text-muted">Not set</span>
          )}
          <a href={provider.docsUrl} target="_blank" rel="noopener" className="text-muted hover:text-primary">
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Input
            type={show ? "text" : "password"}
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder={existing?.is_active ? "••••••••••••••• (update)" : provider.placeholder}
            className="pr-10"
            onKeyDown={(e) => e.key === "Enter" && void save()}
          />
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        <Button onClick={save} loading={saving} disabled={!key.trim() || saving} size="sm">
          Save
        </Button>
      </div>
      {err && <p className="text-xs text-critical">{err}</p>}
      {msg && <p className="text-xs text-healthy">{msg}</p>}
    </div>
  );
}

// ── TelegramKeyForm component ─────────────────────────────────────────────
function TelegramKeyForm({ existing, onSaved }: { existing?: ApiKeyItem; onSaved: () => void }) {
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    if (!token.trim()) return;
    setSaving(true);
    setErr(null);
    setMsg(null);
    // Save bot token as telegram provider key
    const res = await apiClient<{ connected: boolean; bot_username: string }>("/api/v1/integrations/telegram/connect", {
      method: "POST",
      body: JSON.stringify({ bot_token: token, telegram_username: username || null }),
    });
    setSaving(false);
    if (res.error) setErr(res.error.detail || "Failed to save.");
    else { setMsg(`@${res.data?.bot_username || "bot"} connected and ready.`); setToken(""); onSaved(); }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="text-xs text-muted">Bot Token</label>
          <div className="relative mt-1">
            <Input
              type={show ? "text" : "password"}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={existing?.is_active ? "••••• (update token)" : "123456789:ABC..."}
              className="pr-10"
            />
            <button type="button" onClick={() => setShow((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink">
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className="text-[11px] text-muted mt-1">From @BotFather → /newbot</p>
        </div>
        <div>
          <label className="text-xs text-muted">Your Telegram Username (optional)</label>
          <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="@yourusername" className="mt-1" />
          <p className="text-[11px] text-muted mt-1">To restrict bot to your account only</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button onClick={save} loading={saving} disabled={!token.trim() || saving}>
          Save Telegram Bot
        </Button>
        {existing?.is_active && (
          <span className="flex items-center gap-1 text-xs text-healthy">
            <CheckCircle2 className="h-3.5 w-3.5" /> Bot active
          </span>
        )}
      </div>
      {err && <p className="text-xs text-critical">{err}</p>}
      {msg && <p className="text-xs text-healthy">{msg}</p>}
      <div className="rounded-2xl bg-mist/60 p-4 text-xs text-muted space-y-1">
        <p>📱 <strong>How to use:</strong></p>
        <p>1. Create bot with @BotFather → /newbot → copy token above</p>
        <p>2. Message your bot on Telegram — Xomni responds using NVIDIA + Groq</p>
        <p>3. All chat history is saved to your account</p>
      </div>
    </div>
  );
}
