"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { loginSchema, type LoginInput } from "@/lib/validations/auth";
import { apiClient, setAccessToken } from "@/lib/auth-client";

type LoginResponse = {
  user?: { email: string; is_verified: boolean };
  tokens?: { access_token: string } | null;
  tfa_required?: boolean;
  message?: string;
};

export function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get("next") || "/app";
  const [serverError, setServerError] = useState<string | null>(null);
  const [needsTotp, setNeedsTotp] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const { data, error } = await apiClient<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: values.email,
        password: values.password,
        totp_code: values.totp_code || undefined,
      }),
    });

    if (error) {
      setServerError(error.detail || "Sign in failed.");
      return;
    }
    if (data?.tfa_required) {
      setNeedsTotp(true);
      setServerError("Enter your authenticator code to continue.");
      return;
    }
    if (data?.tokens?.access_token) {
      setAccessToken(data.tokens.access_token);
      router.replace(next);
      router.refresh();
      return;
    }
    setServerError(data?.message || "Unable to sign in.");
  });

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
        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        {needsTotp ? (
          <Input
            label="Authenticator code"
            inputMode="numeric"
            autoComplete="one-time-code"
            error={errors.totp_code?.message}
            {...register("totp_code")}
          />
        ) : null}
        {serverError ? (
          <p className="text-sm text-critical" role="alert">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Sign in
        </Button>
        <div className="flex items-center justify-between text-sm">
          <Link href="/forgot-password" className="text-muted hover:text-ink">
            Forgot password?
          </Link>
          <Link href="/register" className="font-medium text-primary hover:underline">
            Create account
          </Link>
        </div>
      </form>
    </Card>
  );
}
