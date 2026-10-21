"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  ErrorState,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/auth-client";
import { useSearchParams, useRouter } from "next/navigation";

type ProviderModel = {
  provider: "nvidia" | "openai" | "gemini" | "groq" | "ollama" | "mock";
  model: string;
  name: string;
};

type ApiKeyFormState = {
  isSubmitting: boolean;
  error: string | null;
};

export default function ProfileApiKeysPage() {
  const [keys, setKeys] = useState<{
    id: string;
    provider: string;
    is_active: boolean;
  }[] | null>(null);
  const [provider, setProvider] = useState<"nvidia" | "openai" | "gemini" | "groq" | "ollama" | "mock">(
    "nvidia"
  );
  const [model, setModel] = useState<string>("nvidia/nemotron-3.5-lightning-30b-a3b");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Available models per provider
  const availableModels: Record<string, { model: string; name: string }> = {
    nvidia: {
      model: "nvidia/nemotron-3.5-lightning-30b-a3b",
      name: "Nemotron 3.5 Lightning",
    },
    openai: {
      model: "gpt-4o-mini",
      name: "GPT-4o Mini",
    },
    gemini: {
      model: "gemini-1.5-flash",
      name: "Gemini 1.5 Flash",
    },
    groq: {
      model: "openai/gpt-oss-120b",
      name: "GPT-OSS 120B (Groq)",
    },
    ollama: {
      model: "llama3",
      name: "Llama 3 (local)",
    },
    mock: {
      model: "mock-model",
      name: "Mock (demo mode)",
    },
  };

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [me, acc] = await Promise.all([
        apiClient<any>("/api/v1/auth/me"),
        apiClient<{ id: string; provider: string; is_active: boolean }[]>("/api/v1/profile/api-keys"),
      ]);

      if (me.error) {
        setError(me.error.detail || "Failed to load profile. Please sign in again.");
        setKeys(null);
        return;
      }

      setKeys(acc.data || []);
    } catch (e) {
      setError("Failed to load API keys. Please try again.");
      setKeys(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAddKey = useCallback(
    async (providerName: string, apiKey: string) => {
      setError(null);
      setLoading(true);
      try {
        await apiClient("/api/v1/profile/api-keys", {
          method: "POST",
          body: JSON.stringify({
            provider: providerName,
            api_key: apiKey,
          }),
        });
        setSuccess(`API key for ${providerName} added successfully!`);
        void load();
      } catch (e: any) {
        setError(e.response?.detail || "Failed to add API key. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const handleRemoveKey = useCallback(
    async (providerName: string) => {
      setError(null);
      setLoading(true);
      try {
        await apiClient("/api/v1/profile/api-keys/" + providerName, {
          method: "DELETE",
        });
        setSuccess(`API key for ${providerName} removed successfully!`);
        void load();
      } catch (e: any) {
        setError(e.response?.detail || "Failed to remove API key. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="font-display text-3xl font-semibold tracking-tight text-ink">
          API Keys
        </h2>
        <p className="text-sm text-muted">Loading...</p>
        <Skeleton className="h-6 w-64" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h2 className="font-display text-3xl font-semibold tracking-tight text-ink">
          API Keys
        </h2>
        <ErrorState description={error} onRetry={() => void load()} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
          API Keys
        </h1>
        <p className="text-sm text-muted">
          Manage your LLM provider API keys to enable AI features
        </p>
      </div>

      {error ? (
        <ErrorState description={error} onRetry={() => void load()} />
      ) : null}

      {success && (
        <div className="rounded-[1.75rem] bg-success/5 px-4 py-2 text-sm text-success">
          {success}
        </div>
      )}

      {/* Add New Provider Form */}
      <Card>
        <CardHeader>
          <p className="text-sm font-semibold text-ink">Add LLM Provider API Key</p>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold text-muted">Provider</p>
            <Input
              type="hidden"
              value={provider}
              onChange={(e) => setProvider(e.target.value as any)}
            />
            <div className="mt-2 space-y-1">
              {Object.keys(availableModels).map((prov) => (
                <label
                  key={prov}
                  className={`flex items-center gap-2 rounded border ${
                    prov === provider
                      ? "border-primary bg-primary/10"
                      : "border-muted/20 hover:bg-primary/5"
                  }`}
                >
                  <input
                    type="radio"
                    name="provider"
                    value={prov}
                    checked={prov === provider}
                    onChange={(e) =>
                      setProvider(e.target.value as "nvidia" | "openai" | "gemini" | "groq" | "ollama" | "mock")
                    }
                  />
                  <span className="text-sm font-medium text-ink">
                    {prov === "nvidia"
                      ? "NVIDIA NIM"
                      : prov === "openai"
                      ? "OpenAI"
                      : prov === "gemini"
                      ? "Google Gemini"
                      : prov === "groq"
                      ? "Groq"
                      : prov === "ollama"
                      ? "Ollama (local)"
                      : "Mock"}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-muted">API Key</p>
            <Input
              type="password"
              placeholder="Enter your API key"
              required
              className="w-full"
              disabled={loading}
            />
          </div>

          <div className="flex gap-2 mt-4">
            <Button
              disabled={loading}
              type="submit"
              onClick={() => {}}
            >
              Add Key
            </Button>
            <Button
              type="button"
              onClick={() => {}}
              variant="outline"
              disabled={loading}
            >
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Existing Keys List */}
      {keys && keys.length > 0 && (
        <Card>
          <CardHeader>
            <p className="text-sm font-semibold text-ink">Your Active Provider Keys</p>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {keys.map((key) => (
                <div
                  key={key.id}
                  className="rounded-2xl bg-mist/60 px-4 py-2 flex items-center justify-between text-sm"
                >
                  <span className="font-medium text-ink capitalize">
                    {key.provider === "nvidia"
                      ? "NVIDIA NIM"
                      : key.provider === "openai"
                      ? "OpenAI"
                      : key.provider === "gemini"
                      ? "Google Gemini"
                      : key.provider === "groq"
                      ? "Groq"
                      : key.provider === "ollama"
                      ? "Ollama (local)"
                      : "Mock"}
                  </span>
                  <span className="text-muted">
                    {key.is_active ? "Active" : "Inactive"}
                  </span>
                  {key.is_active && (
                    <Button
                      size="icon"
                        variant="ghost"
                        onClick={() => {}}
                        aria-label="Configure"
                    >
                      ⚙️
                    </Button>
                  )}
                  {!key.is_active && (
                    <Button
                      size="icon"
                        variant="ghost"
                        onClick={() => {}}
                        aria-label="Reactivate"
                      >
                        ⏳
                      </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Model Selection Info */}
      {keys && keys.length > 0 && (
        <Card>
          <CardHeader>
            <p className="text-sm font-semibold text-ink">Selected Model</p>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-ink">
              Currently selected: <strong className="font-semibold">
                {provider === "nvidia"
                  ? "Nemotron 3.5 Lightning (NVIDIA NIM)"
                  : provider === "openai"
                  ? "GPT-4o Mini (OpenAI)"
                  : provider === "gemini"
                  ? "Gemini 1.5 Flash (Google)"
                  : provider === "groq"
                  ? "Llama 3.1 8B Instant (Groq)"
                  : provider === "ollama"
                  ? "Llama 3 (Ollama local)"
                  : "Mock (demo)"}
                </strong>
            </p>
            <p className="text-xs text-muted mt-1">
              Change your provider key in the profile to switch models.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/*Skeleton component placeholder - will be imported from UI library*/
const Skeleton = (props: any) => <div {...props} />;