"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { verifyOtpSchema, type VerifyOtpInput } from "@/lib/validations/auth";
import { apiClient } from "@/lib/auth-client";

export function VerifyForm() {
  const router = useRouter();
  const search = useSearchParams();
  const emailDefault = search.get("email") || "";
  const [serverError, setServerError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<VerifyOtpInput>({
    resolver: zodResolver(verifyOtpSchema),
    defaultValues: { email: emailDefault },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const { error } = await apiClient("/api/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify({
        email: values.email,
        code: values.code,
        purpose: "verify_email",
      }),
    });
    if (error) {
      setServerError(error.detail || "Verification failed.");
      return;
    }
    router.push(`/login?verified=1&email=${encodeURIComponent(values.email)}`);
  });

  const resend = async () => {
    setServerError(null);
    setInfo(null);
    const email = getValues("email");
    const { data, error } = await apiClient<{ message?: string }>("/api/auth/send-otp", {
      method: "POST",
      body: JSON.stringify({ email, purpose: "verify_email" }),
    });
    if (error) {
      setServerError(error.detail || "Could not resend code.");
      return;
    }
    setInfo(data?.message || "Code sent.");
  };

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Input
          label="Email"
          type="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <Input
          label="Verification code"
          inputMode="numeric"
          autoComplete="one-time-code"
          error={errors.code?.message}
          {...register("code")}
        />
        {serverError ? (
          <p className="text-sm text-critical" role="alert">
            {serverError}
          </p>
        ) : null}
        {info ? <p className="text-sm text-healthy">{info}</p> : null}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Verify email
        </Button>
        <button
          type="button"
          onClick={resend}
          className="w-full text-sm font-medium text-primary hover:underline"
        >
          Resend code
        </button>
        <p className="text-center text-sm text-muted">
          <Link href="/login" className="hover:text-ink">
            Back to sign in
          </Link>
        </p>
      </form>
    </Card>
  );
}
