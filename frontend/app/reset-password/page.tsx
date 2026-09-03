import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth/auth-shell";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { Skeleton } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Set new password",
  robots: { index: false, follow: false },
};

export default function ResetPasswordPage() {
  return (
    <AuthShell title="Choose a new password" subtitle="Use the code from your email.">
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <ResetPasswordForm />
      </Suspense>
    </AuthShell>
  );
}
