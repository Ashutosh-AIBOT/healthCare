"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiClient, getAccessToken, setAccessToken } from "@/lib/auth-client";
import { SidebarNav } from "@/components/app/sidebar-nav";
import { TopBar } from "@/components/app/top-bar";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [checking, setChecking] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    const token = getAccessToken();
    if (!token) {
      if (!cancelled) {
        router.replace("/login");
      }
      setChecking(false);
      return;
    }

    apiClient<{ id: string }>("/api/v1/auth/me")
      .then((res) => {
        if (!cancelled && res.error) {
          setAccessToken(null);
          router.replace("/login");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAccessToken(null);
          router.replace("/login");
        }
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, [router]);

  const logout = async () => {
    await apiClient("/api/v1/auth/logout", { method: "POST", body: "{}" });
    setAccessToken(null);
    router.replace("/login");
    router.refresh();
  };

  if (checking) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-paper">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-paper">
      <SidebarNav
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        pathname={pathname}
        onLogout={logout}
      />
      <div className={cn("min-h-dvh", "lg:ml-64")}>
        <TopBar onToggleSidebar={() => setSidebarOpen(true)} />
        <main className={cn("min-h-dvh", "px-4 py-6 md:px-6 md:py-8")}>
          <div className={cn("mx-auto", "max-w-7xl")}>{children}</div>
        </main>
      </div>
    </div>
  );
}
