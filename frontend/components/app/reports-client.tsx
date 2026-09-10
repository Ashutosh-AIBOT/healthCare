"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { Disclaimer } from "@/components/brand";
import { apiClient, getAccessToken } from "@/lib/auth-client";
import { TriangleAlert, UploadCloud, ChevronDown, FileText, Sparkles } from "lucide-react";
import Link from "next/link";

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
      } else {
        const body = new FormData();
        body.append("file", file);
        await fetch(`/api/v1/documents/${urlRes.data.document_id}/upload`, {
          method: "POST",
          body,
          credentials: "include",
          headers: (() => { const token = getAccessToken(); const headers: Record<string, string> = {}; if (token) headers.Authorization = `Bearer ${token}`; return headers; })(),
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

      {error && (
        <div className="flex items-center justify-between rounded-xl border border-danger/30 bg-danger/5 p-4 mb-6">
          <div className="flex items-center gap-3">
            <TriangleAlert className="h-5 w-5 text-danger" />
            <p className="text-[13px] font-medium text-danger">{error}</p>
          </div>
          <button onClick={() => void load()} className="rounded-lg px-3 py-1.5 text-[13px] font-medium text-danger hover:bg-danger/10 transition-colors">
            Retry
          </button>
        </div>
      )}

      <div className="rounded-[1.75rem] border border-border bg-surface p-6 shadow-card space-y-4">
        <div>
          <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Select Family Member</label>
          <div className="relative">
            <select
              className="w-full appearance-none rounded-xl border border-border bg-surface px-4 py-3 pr-10 text-[13px] font-medium text-text-primary outline-none focus:border-accent-gold transition-colors"
              value={memberId}
              onChange={(e) => setMemberId(e.target.value)}
            >
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  Member ID: {m.id.slice(0, 8)}…
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Upload Lab Report</label>
          <div className="relative">
            <input
              type="file"
              accept="application/pdf,.pdf"
              id="file-upload"
              className="peer absolute inset-0 h-full w-full opacity-0 cursor-pointer z-10"
              aria-label="Upload lab report PDF"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void upload(f);
              }}
            />
            <div className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-surface hover:bg-surface-hover peer-focus-visible:border-accent-gold p-8 transition-colors">
              <UploadCloud className="h-8 w-8 text-text-secondary" />
              <p className="text-[13px] font-medium text-text-primary">
                {uploading ? "Uploading document..." : "Click or drag PDF to upload"}
              </p>
              <p className="text-[11px] text-text-secondary">Supported: PDF (up to 10MB)</p>
            </div>
          </div>
        </div>
      </div>

      {!docs?.length ? (
        <div className="rounded-[1.75rem] border border-border bg-surface p-12 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-surface-hover text-text-secondary mb-4">
            <FileText className="h-6 w-6" />
          </div>
          <h3 className="text-[14px] font-semibold text-text-primary">No reports yet</h3>
          <p className="text-[13px] text-text-secondary mt-1">Upload a lab PDF to extract values and ask with citations.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {docs.map((d) => (
            <li key={d.id}>
              <div className="rounded-[1.25rem] border border-border bg-surface p-4 shadow-sm hover:shadow-card transition-shadow">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-hover text-text-secondary">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-[13px] font-semibold text-text-primary">{d.filename}</p>
                      <p className="text-[11px] text-text-secondary">Status: {d.status}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button size="sm" variant="secondary" onClick={() => void ask(d.id)} loading={asking}>
                      <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                      Ask about this report
                    </Button>
                    <Link
                      href={`/app/xomni?mode=reports&member_id=${encodeURIComponent(memberId)}&document_id=${encodeURIComponent(d.id)}`}
                      className="inline-flex h-9 items-center rounded-md border border-border bg-surface px-3 text-xs font-medium text-text-primary transition-colors hover:bg-surface-hover"
                    >
                      Open in Xomni
                    </Link>
                  </div>
                </div>
              </div>
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
