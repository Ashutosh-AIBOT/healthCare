import type { Metadata } from "next";
import { AuthShell } from "@/components/auth/auth-shell";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Create account",
  description: "Create your Aarogya family health account.",
  robots: { index: false, follow: false },
};

export default function RegisterPage() {
  return (
    <AuthShell
      title="Start with your family"
      subtitle="Create an account. Verify email. Then invite the people who matter."
    >
      <RegisterForm />
    </AuthShell>
  );
}
