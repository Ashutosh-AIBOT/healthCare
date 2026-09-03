"use client";

import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { forgotPasswordSchema, type ForgotPasswordInput } from "@/lib/validations/auth";
import { apiClient } from "@/lib/auth-client";

export function ForgotPasswordForm() {
  const [done, setDone] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordInput>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const { error } = await apiClient("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email: values.email }),
    });
    if (error) {
      setServerError(error.detail || "Request failed.");
      return;
    }
    setDone(true);
  });

  if (done) {
    return (
      <Card>
        <p className="text-sm text-muted">
          If an account exists for <strong className="text-ink">{getValues("email")}</strong>, we
          sent a reset code. Check your inbox.
        </p>
        <Link
          href={`/reset-password?email=${encodeURIComponent(getValues("email"))}`}
          className="mt-6 inline-flex text-sm font-semibold text-primary hover:underline"
        >
          Enter reset code →
        </Link>
      </Card>
    );
  }

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        {serverError ? (
          <p className="text-sm text-critical" role="alert">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Send reset code
        </Button>
        <p className="text-center text-sm text-muted">
          <Link href="/login" className="hover:text-ink">
            Back to sign in
          </Link>
        </p>
      </form>
    </Card>
  );
}
