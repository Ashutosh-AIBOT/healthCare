import Link from "next/link";
import { Logo, Disclaimer } from "@/components/brand";

export function SiteFooter() {
  return (
    <footer className="border-t border-line/60 bg-foam py-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 md:flex-row md:items-start md:justify-between md:px-8">
        <div>
          <Logo />
          <Disclaimer className="mt-3 max-w-sm" />
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
          <Link href="/features" className="hover:text-ink">Features</Link>
          <Link href="/pricing" className="hover:text-ink">Pricing</Link>
          <Link href="/for-doctors" className="hover:text-ink">Doctors</Link>
          <Link href="/for-labs" className="hover:text-ink">Labs</Link>
          <Link href="/legal/medical-disclaimer" className="hover:text-ink">Disclaimer</Link>
          <Link href="/legal/privacy" className="hover:text-ink">Privacy</Link>
          <Link href="/legal/terms" className="hover:text-ink">Terms</Link>
        </div>
      </div>
    </footer>
  );
}
