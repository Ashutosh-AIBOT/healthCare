"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type Member = {
  id: string;
  relation?: string | null;
  date_of_birth?: string | null;
  is_dependent?: boolean;
  conditions?: string;
  medications?: string;
};

type Invite = {
  id: string;
  email: string;
  status: string;
  relation?: string | null;
  token?: string;
};

export function MembersClient() {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [relation, setRelation] = useState("spouse");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [grantsMsg, setGrantsMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const fam = await apiClient<{ id: string } | null>("/api/v1/families/me");
    if (fam.error) {
      setError(fam.error.detail || "Could not load family.");
      setMembers([]);
      return;
    }
    if (!fam.data) {
      const created = await apiClient<{ id: string }>("/api/v1/families/", {
        method: "POST",
        body: JSON.stringify({ name: "My family" }),
      });
      if (created.error) {
        setError(created.error.detail || "Create a family first.");
        setMembers([]);
        return;
      }
    }
    const [m, inv] = await Promise.all([
      apiClient<Member[]>("/api/v1/families/members"),
      apiClient<Invite[]>("/api/v1/families/invites"),
    ]);
    if (m.error) {
      setError(m.error.detail || "Failed to load members.");
      setMembers([]);
      return;
    }
    setMembers(m.data || []);
    setInvites(inv.data || []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const sendInvite = async () => {
    setBusy(true);
    setError(null);
    const { error: err } = await apiClient("/api/v1/families/invites", {
      method: "POST",
      body: JSON.stringify({
        email,
        role: "family_member",
        relation,
        expires_in_hours: 14 * 24,
      }),
    });
    setBusy(false);
    if (err) {
      setError(err.detail || "Invite failed.");
      return;
    }
    setEmail("");
    await load();
  };

  const grantDefaults = async (subjectId: string) => {
    if (!members || members.length < 2) return;
    const viewer = members.find((m) => m.id !== subjectId);
    if (!viewer) return;
    setGrantsMsg(null);
    const { error: err } = await apiClient(`/api/v1/families/members/${subjectId}/visibility`, {
      method: "PUT",
      body: JSON.stringify({
        grants: [
          { viewer_member_id: viewer.id, field_key: "health_score", level: "view" },
          { viewer_member_id: viewer.id, field_key: "activity", level: "view" },
          { viewer_member_id: viewer.id, field_key: "appointments", level: "view" },
        ],
      }),
    });
    if (err) {
      setGrantsMsg(err.detail || "Could not update grants.");
      return;
    }
    setGrantsMsg("Grants updated for selected member.");
    setSelected(subjectId);
  };

  if (members === null && !error) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error && members === null) {
    return <ErrorState description={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Family</h1>
        <p className="mt-2 text-sm text-muted">
          Members, invites, and per-field visibility. Ungranted fields stay invisible.
        </p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      {!members?.length ? (
        <EmptyState
          title="No members yet"
          description="Create your family space and invite relatives. You control what each person can see."
        />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {members.map((m) => (
            <li key={m.id}>
              <Card>
                <p className="font-semibold text-ink">{m.relation || "Member"}</p>
                <p className="mt-1 font-mono text-xs text-muted">{m.id.slice(0, 8)}…</p>
                {"conditions" in m ? (
                  <p className="mt-3 text-sm text-muted">Conditions shared with you.</p>
                ) : (
                  <p className="mt-3 text-sm text-muted">Medical fields hidden unless granted.</p>
                )}
                <Button
                  size="sm"
                  variant="secondary"
                  className="mt-4"
                  onClick={() => void grantDefaults(m.id)}
                >
                  Grant spouse-level fields to another member
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {grantsMsg ? <p className="text-sm text-healthy">{grantsMsg}</p> : null}
      {selected ? (
        <p className="text-xs text-muted">Last grant subject: {selected.slice(0, 8)}…</p>
      ) : null}

      <Card>
        <h2 className="font-semibold">Invite someone</h2>
        <div className="mt-4 space-y-3">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label="Relation"
            value={relation}
            onChange={(e) => setRelation(e.target.value)}
            hint="spouse, sibling, parent, adult_child, guardian, other"
          />
          <Button loading={busy} onClick={() => void sendInvite()} disabled={!email}>
            Send invite
          </Button>
        </div>
      </Card>

      {invites.length ? (
        <div>
          <h2 className="font-semibold">Pending invites</h2>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            {invites.map((i) => (
              <li key={i.id} className="flex justify-between gap-4 border-b border-line/50 py-2">
                <span>
                  {i.email} · {i.status}
                  {i.relation ? ` · ${i.relation}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
