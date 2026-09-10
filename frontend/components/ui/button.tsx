import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg" | "icon";

const variants: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground shadow-lift hover:brightness-95 active:translate-y-px",
  secondary:
    "border border-line bg-foam/80 text-ink hover:border-primary/30 hover:bg-primary-soft/40",
  ghost: "text-muted hover:text-ink hover:bg-mist/60",
  danger: "bg-critical text-foam hover:opacity-90 active:scale-[0.98]",
  outline: "border border-line bg-surface text-ink hover:bg-mist",
};

const sizes: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-5 py-2.5 text-sm",
  lg: "px-6 py-3.5 text-sm",
  icon: "h-10 w-10 rounded-full p-0",
};

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-[background-color,border-color,color,transform,opacity] duration-150 ease-soft disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />
      ) : null}
      {children}
    </button>
  ),
);
Button.displayName = "Button";
