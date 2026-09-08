"use client";

export function MedicalNote({ compact = false }: { compact?: boolean }) {
  return (
    <div
      role="note"
      aria-label="Medical disclaimer"
      className="rounded-2xl border border-line bg-mist/50 px-4 py-3"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">
        General information
      </p>
      {!compact ? (
        <p className="mt-1 text-sm text-muted">
          This is educational content, not medical advice. Nutrition values are
          per 100 g approximations and test guidance is general information.
          Always confirm with your doctor before acting on it.
        </p>
      ) : (
        <p className="mt-1 text-xs text-muted">
          Educational content — confirm with your doctor.
        </p>
      )}
    </div>
  );
}
