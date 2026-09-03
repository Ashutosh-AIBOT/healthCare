import Link from "next/link";
import { EmptyState } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Disclaimer } from "@/components/brand";

export default function AppHomePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Family home</h1>
        <p className="mt-2 max-w-xl text-sm text-muted">
          Upload a report, invite family with field-level access, or ask about a recent marker.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <EmptyState
          title="No reports yet"
          description="Upload a lab PDF to extract values and get a cited explanation."
          action={
            <Link href="/app/reports">
              <Button size="sm">Go to reports</Button>
            </Link>
          }
        />
        <EmptyState
          title="Invite your family"
          description="Share only the fields you choose. Ungranted data stays invisible."
          action={
            <Link href="/app/members">
              <Button size="sm" variant="secondary">
                Manage family
              </Button>
            </Link>
          }
        />
      </div>
      <Disclaimer />
    </div>
  );
}
