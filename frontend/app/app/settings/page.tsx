import { Card } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-2 text-sm text-muted">Security, sessions, and consents.</p>
      </div>
      <Card>
        <h2 className="font-semibold">Account security</h2>
        <p className="mt-2 text-sm text-muted">
          Password change, 2FA enrollment, and session list will connect to{" "}
          <code className="font-mono text-xs">/api/v1/auth/*</code> next.
        </p>
      </Card>
    </div>
  );
}
