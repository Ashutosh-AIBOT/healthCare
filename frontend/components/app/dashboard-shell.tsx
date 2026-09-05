"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { apiClient, setAccessToken } from "@/lib/auth-client";
import { SidebarNav } from "@/components/app/sidebar-nav";
import { TopBar } from "@/components/app/top-bar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const logout = async () => {
    await apiClient("/api/auth/logout", { method: "POST", body: "{}" });
    setAccessToken(null);
    router.replace("/login");
    router.refresh();
  };

  return (
    <div className="min-h-dvh bg-paper">
      <SidebarNav
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        pathname={pathname}
        onLogout={logout}
      />
      <div className="lg:ml-64">
        <TopBar onToggleSidebar={() => setSidebarOpen(true)} />
        <main className="px-4 py-6 md:px-6 md:py-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
