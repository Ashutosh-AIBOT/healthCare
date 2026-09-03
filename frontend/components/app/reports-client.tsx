"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { Disclaimer } from "@/components/brand";
import { apiClient, getAccessToken } from "@/lib/auth-client";

type Doc = { id: string; filename: string; status: string; job_id?: string | null };
type Member = { id: string };

export function ReportsClient() {
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [memberId, setMemberId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState("What does my hemoglobin mean?");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    const [d, m] = await Promise.all([
      apiClient<Doc[]>("/api/v1/documents"),
      apiClient<Member[]>("/api/v1/families/members"),
    ]);
    if (d.error) {
      setError(d.error.detail || "Could not load reports.");
      setDocs([]);
      return;
    }
    setDocs(d.data || []);
    setMembers(m.data || []);
    if (m.data?.[0] && !memberId) setMemberId(m.data[0].id);
  }, [memberId]);

  useEffect(() => {
    void load();
  }, [load]);

  const upload = async (file: File) => {
    if (!memberId) {
      setError("Select a family member first.");
      return;
    }
    setUploading(true);
    setError(null);
    const urlRes = await apiClient<{
      upload_url: string;
      object_key: string;
      document_id: string;
    }>("/api/v1/documents/upload-url", {
      method: "POST",
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || "application/pdf",
        member_id: memberId,
        byte_size: file.size,
      }),
    });
    if (urlRes.error || !urlRes.data) {
      setUploading(false);
      setError(urlRes.error?.detail || "Could not get upload URL.");
      return;
    }

    try {
      if (urlRes.data.upload_url.startsWith("http")) {
        await fetch(urlRes.data.upload_url, {
          method: "PUT",
          body: file,
          headers: { "Content-Type": file.type || "application/pdf" },
        });
      }
    } catch {
      /* local fallback */
    }

    const confirm = await apiClient<{ document_id: string; job_id: string }>("/api/v1/documents", {
      method: "POST",
      body: JSON.stringify({
        document_id: urlRes.data.document_id,
      }),
    });
    setUploading(false);
    if (confirm.error) {
      setError(confirm.error.detail || "Confirm upload failed.");
      return;
    }
    await load();
  };

  const ask = async (documentId?: string) => {
    if (!memberId) return;
    setAsking(true);
    setAnswer("");
    setError(null);
    const token = getAccessToken();
    const res = await fetch("/api/v1/ai/ask", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        member_id: memberId,
        document_id: documentId,
        question,
      }),
    });
    if (!res.ok || !res.body) {
      setAsking(false);
      setError("Ask failed.");
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // SSE: data: ...
      const parts = buf.split("\n");
      buf = parts.pop() || "";
      for (const line of parts) {
        if (line.startsWith("data:")) {
          setAnswer((prev) => prev + line.slice(5).trimStart() + "\n");
        }
      }
    }
    setAsking(false);
  };

  if (docs === null && !error) {
    return <Skeleton className="h-48 w-full" />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Reports</h1>
        <p className="mt-2 text-sm text-muted">
          Upload a PDF, wait for processing, then ask a cited question.
        </p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      <Card>
        <label className="block text-sm font-medium">Member</label>
        <select
          className="mt-1.5 w-full rounded-2xl border border-line bg-surface px-4 py-3 text-sm"
          value={memberId}
          onChange={(e) => setMemberId(e.target.value)}
        >
          {members.map((m) => (
            <option key={m.id} value={m.id}>
              {m.id.slice(0, 8)}…
            </option>
          ))}
        </select>
        <div className="mt-4">
          <input
            type="file"
            accept="application/pdf,.pdf"
            aria-label="Upload lab report PDF"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void upload(f);
            }}
          />
          {uploading ? <p className="mt-2 text-sm text-muted">Uploading…</p> : null}
        </div>
      </Card>

      {!docs?.length ? (
        <EmptyState
          title="No reports yet"
          description="Upload a lab PDF to extract values and ask with citations."
        />
      ) : (
        <ul className="space-y-3">
          {docs.map((d) => (
            <li key={d.id}>
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold">{d.filename}</p>
                    <p className="text-xs text-muted">Status: {d.status}</p>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => void ask(d.id)} loading={asking}>
                    Ask about this report
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <Card>
        <Input label="Question" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <Button className="mt-4" onClick={() => void ask(docs?.[0]?.id)} loading={asking}>
          Ask
        </Button>
        {answer ? (
          <pre className="mt-4 whitespace-pre-wrap rounded-2xl bg-mist/50 p-4 text-sm text-ink">
            {answer}
          </pre>
        ) : null}
        <Disclaimer className="mt-4" />
      </Card>
    </div>
  );
}
