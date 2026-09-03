import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth/auth-shell";
import { LoginForm } from "@/components/auth/login-form";
import { Skeleton } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to your Aarogya family health space.",
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return (
    <AuthShell title="Welcome back" subtitle="Sign in to your family health space.">
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
