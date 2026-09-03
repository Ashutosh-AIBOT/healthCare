"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { resetPasswordSchema, type ResetPasswordInput } from "@/lib/validations/auth";
import { apiClient } from "@/lib/auth-client";

export function ResetPasswordForm() {
  const router = useRouter();
  const search = useSearchParams();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordInput>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { email: search.get("email") || "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const { error } = await apiClient("/api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({
        email: values.email,
        otp: values.otp,
        new_password: values.new_password,
      }),
    });
    if (error) {
      setServerError(error.detail || "Could not reset password.");
      return;
    }
    router.push("/login?reset=1");
  });

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Input label="Email" type="email" error={errors.email?.message} {...register("email")} />
        <Input
          label="Reset code"
          inputMode="numeric"
          error={errors.otp?.message}
          {...register("otp")}
        />
        <Input
          label="New password"
          type="password"
          autoComplete="new-password"
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register("confirm_password")}
        />
        {serverError ? (
          <p className="text-sm text-critical" role="alert">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Update password
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
