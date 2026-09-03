import { z } from "zod";

export const passwordSchema = z
  .string()
  .min(8, "At least 8 characters")
  .max(128)
  .regex(/[a-z]/, "Include a lowercase letter")
  .regex(/[A-Z]/, "Include an uppercase letter")
  .regex(/\d/, "Include a number");

export const handleSchema = z
  .string()
  .min(3)
  .max(30)
  .regex(/^[a-z][a-z0-9_]*$/, "Start with a letter; use a-z, 0-9, _ only")
  .transform((v) => v.toLowerCase());

export const registerSchema = z
  .object({
    full_name: z.string().min(1, "Name is required").max(120),
    handle: handleSchema,
    email: z.string().email("Enter a valid email"),
    password: passwordSchema,
    confirm_password: z.string(),
    accept_terms: z.literal(true, {
      errorMap: () => ({ message: "Accept the terms to continue" }),
    }),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
  totp_code: z.string().max(12).optional(),
});

export const verifyOtpSchema = z.object({
  email: z.string().email(),
  code: z.string().min(4, "Enter the code").max(12),
});

export const forgotPasswordSchema = z.object({
  email: z.string().email("Enter a valid email"),
});

export const resetPasswordSchema = z
  .object({
    email: z.string().email(),
    otp: z.string().min(4).max(12),
    new_password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type RegisterInput = z.infer<typeof registerSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type VerifyOtpInput = z.infer<typeof verifyOtpSchema>;
export type ForgotPasswordInput = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordInput = z.infer<typeof resetPasswordSchema>;
