"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Logo } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { apiClient, setAccessToken } from "@/lib/auth-client";

const nav = [
  { href: "/app", label: "Home" },
  { href: "/app/reports", label: "Reports" },
  { href: "/app/members", label: "Family" },
  { href: "/app/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const logout = async () => {
    await apiClient("/api/auth/logout", { method: "POST", body: "{}" });
    setAccessToken(null);
    router.replace("/login");
    router.refresh();
  };

  return (
    <div className="min-h-dvh bg-[linear-gradient(180deg,var(--color-mist)_0%,var(--color-foam)_28%,var(--color-foam)_100%)]">
      <header className="sticky top-0 z-30 border-b border-line/50 bg-foam/85 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 md:px-6">
          <div className="flex items-center gap-8">
            <Logo href="/app" className="text-lg" />
            <nav className="hidden items-center gap-1 md:flex" aria-label="App">
              {nav.map((item) => {
                const active =
                  pathname === item.href || (item.href !== "/app" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors duration-300 ease-soft",
                      active ? "bg-primary text-primary-foreground shadow-lift" : "text-muted hover:bg-mist hover:text-ink",
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
        <nav
          className="flex gap-1 overflow-x-auto border-t border-line/40 px-4 py-2 md:hidden"
          aria-label="App mobile"
        >
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "shrink-0 rounded-full px-3 py-1.5 text-xs font-medium",
                pathname === item.href ? "bg-primary text-primary-foreground" : "text-muted",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 md:px-6 md:py-12">{children}</main>
    </div>
  );
}
