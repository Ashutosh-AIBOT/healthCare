import Link from "next/link";
import type { Metadata } from "next";
import { Logo } from "@/components/brand";
import { EmptyState } from "@/components/ui/card";

export const metadata: Metadata = { title: "Doctor · Patients", robots: { index: false } };

export default function DoctorPatientsPage() {
  return (
    <div className="min-h-dvh bg-mist/40">
      <header className="border-b border-line/60 bg-foam px-4 py-3">
        <Logo href="/doctor" />
      </header>
      <main className="mx-auto max-w-6xl px-4 py-10">
        <EmptyState
          title="No consented patients"
          description="Patients appear only after a consent grant for the encounter."
          action={
            <Link href="/doctor" className="text-sm font-semibold text-primary hover:underline">
              ← Back
            </Link>
          }
        />
      </main>
    </div>
  );
}
