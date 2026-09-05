"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";
import { useTheme } from "@/components/theme-provider";

export default function SettingsPage() {
  const [messagingVisible, setMessagingVisible] = useState(true);
  const [familyVisible, setFamilyVisible] = useState(true);
  const [relationsVisible, setRelationsVisible] = useState(true);
  const [allowedVisible, setAllowedVisible] = useState(true);
  const { theme, resolved, setTheme } = useTheme();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Settings</h1>
        <p className="mt-2 text-sm text-muted">Security, sessions, and consents.</p>
      </div>

      <Card>
        <h2 className="font-semibold text-ink">Appearance</h2>
        <p className="mt-1 text-xs text-muted">Choose how the app looks for you.</p>
        <div className="mt-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm text-ink">Theme</p>
            <p className="text-xs text-muted">
              Current preference: <span className="font-semibold">{theme}</span>{" "}
              <span className="text-muted">(resolved: {resolved})</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTheme("light")}
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition-colors duration-300 ease-soft ${
                theme === "light"
                  ? "border-primary bg-primary-soft text-primary"
                  : "border-line bg-surface text-muted hover:bg-mist hover:text-ink"
              }`}
            >
              Light
            </button>
            <button
              type="button"
              onClick={() => setTheme("dark")}
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition-colors duration-300 ease-soft ${
                theme === "dark"
                  ? "border-primary bg-primary-soft text-primary"
                  : "border-line bg-surface text-muted hover:bg-mist hover:text-ink"
              }`}
            >
              Dark
            </button>
            <button
              type="button"
              onClick={() => setTheme("system")}
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition-colors duration-300 ease-soft ${
                theme === "system"
                  ? "border-primary bg-primary-soft text-primary"
                  : "border-line bg-surface text-muted hover:bg-mist hover:text-ink"
              }`}
            >
              System
            </button>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold text-ink">Sidebar visibility</h2>
        <p className="mt-1 text-xs text-muted">Choose which items appear in the app sidebar.</p>
        <div className="mt-4 space-y-3">
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Messaging</span>
            <input
              type="checkbox"
              checked={messagingVisible}
              onChange={(e) => setMessagingVisible(e.target.checked)}
              className="h-4 w-4 rounded border-line accent-primary"
            />
          </label>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Family</span>
            <input
              type="checkbox"
              checked={familyVisible}
              onChange={(e) => setFamilyVisible(e.target.checked)}
              className="h-4 w-4 rounded border-line accent-primary"
            />
          </label>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm text-ink">Relations</span>
            <input
              type="checkbox"
              checked={relationsVisible}
              onChange={(e) => setRelationsVisible(e.target.checked)}
              className="h-4 w-4 rounded border-line accent-primary"
            />
          </label>
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold text-ink">Allowed list</h2>
        <p className="mt-1 text-xs text-muted">Control family member visibility for shared data.</p>
        <div className="mt-4 space-y-3">
          <label className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-ink">Show family members in reports</p>
              <p className="text-xs text-muted">Members with access can view shared reports.</p>
            </div>
            <input
              type="checkbox"
              checked={allowedVisible}
              onChange={(e) => setAllowedVisible(e.target.checked)}
              className="h-4 w-4 rounded border-line accent-primary"
            />
          </label>
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold text-ink">Account security</h2>
        <p className="mt-2 text-sm text-muted">
          Password change, 2FA enrollment, and session list will connect to{" "}
          <code className="font-mono text-xs">/api/v1/auth/*</code> next.
        </p>
      </Card>
    </div>
  );
}
