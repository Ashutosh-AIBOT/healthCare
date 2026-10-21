"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  if (error) {
    // Intentionally minimal: root-level fallback when even the layout fails.
    console.error(error);
  }

  return (
    <html>
      <body className="min-h-dvh bg-bg text-text-primary flex items-center justify-center px-6">
        <div className="max-w-md text-center space-y-4">
          <h2 className="text-2xl font-semibold">Something went wrong</h2>
          <p className="text-text-secondary text-sm">
            We couldn’t load this page. You can try again or go back home.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => reset()}
              className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
            >
              Try again
            </button>
            <a
              href="/"
              className="rounded-full border border-border px-5 py-2.5 text-sm font-semibold text-text-primary"
            >
              Go home
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
