import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth/auth-shell";
import { VerifyForm } from "@/components/auth/verify-form";
import { Skeleton } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Verify email",
  robots: { index: false, follow: false },
};

export default function VerifyPage() {
  return (
    <AuthShell title="Verify your email" subtitle="Enter the code we sent to complete signup.">
      <Suspense fallback={<Skeleton className="h-48 w-full" />}>
        <VerifyForm />
      </Suspense>
    </AuthShell>
  );
}
