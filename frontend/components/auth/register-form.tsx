"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { registerSchema, type RegisterInput } from "@/lib/validations/auth";
import { apiClient } from "@/lib/auth-client";

const CONSENT = {
  terms_version: "2026-09-01",
  privacy_version: "2026-09-01",
  medical_disclaimer_version: "2026-09-01",
};

export function RegisterForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: { accept_terms: undefined as unknown as true },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const { error } = await apiClient("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: values.full_name,
        handle: values.handle,
        email: values.email,
        password: values.password,
        ...CONSENT,
      }),
    });
    if (error) {
      setServerError(error.detail || "Could not create account.");
      return;
    }
    router.push(`/verify?email=${encodeURIComponent(values.email)}`);
  });

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Input
          label="Full name"
          autoComplete="name"
          error={errors.full_name?.message}
          {...register("full_name")}
        />
        <Input
          label="Handle"
          hint="Public @handle — lowercase letters, numbers, underscore"
          autoComplete="username"
          error={errors.handle?.message}
          {...register("handle")}
        />
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
          autoComplete="new-password"
          hint="Min 8 chars with upper, lower, and a number"
          error={errors.password?.message}
          {...register("password")}
        />
        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register("confirm_password")}
        />
        <label className="flex items-start gap-3 text-sm text-muted">
          <input
            type="checkbox"
            className="mt-1 rounded border-line text-primary focus:ring-primary"
            {...register("accept_terms")}
          />
          <span>
            I agree to the{" "}
            <Link href="/legal/terms" className="text-primary underline-offset-2 hover:underline">
              Terms
            </Link>
            ,{" "}
            <Link href="/legal/privacy" className="text-primary underline-offset-2 hover:underline">
              Privacy Policy
            </Link>
            , and{" "}
            <Link
              href="/legal/medical-disclaimer"
              className="text-primary underline-offset-2 hover:underline"
            >
              Medical Disclaimer
            </Link>
            .
          </span>
        </label>
        {errors.accept_terms ? (
          <p className="text-xs text-critical" role="alert">
            {errors.accept_terms.message}
          </p>
        ) : null}
        {serverError ? (
          <p className="text-sm text-critical" role="alert">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create account
        </Button>
        <p className="text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </Card>
  );
}
