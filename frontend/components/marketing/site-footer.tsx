import Link from "next/link";
import { Logo, Disclaimer } from "@/components/brand";
import { cn } from "@/lib/utils";

const links = [
  { href: "/features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
  { href: "/for-doctors", label: "Doctors" },
  { href: "/for-labs", label: "Labs" },
  { href: "/legal/medical-disclaimer", label: "Disclaimer" },
  { href: "/legal/privacy", label: "Privacy" },
  { href: "/legal/terms", label: "Terms" },
];

export function SiteFooter({ tone = "light" }: { tone?: "light" | "dark" }) {
  const dark = tone === "dark";
  return (
    <footer className={cn(dark ? "bg-home-dark" : "border-t border-line/60 bg-foam", "py-10")}>
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 md:flex-row md:items-start md:justify-between md:px-8">
        <div>
          <Logo className={dark ? "text-home-primary-dark" : undefined} />
          <Disclaimer className={cn("mt-3 max-w-sm", dark && "text-home-secondary-dark")} />
        </div>
        <div className={cn("flex flex-wrap gap-x-6 gap-y-2 text-sm", dark ? "text-home-secondary-dark" : "text-muted")}>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "transition-colors duration-120",
                dark ? "hover:text-home-primary-dark" : "hover:text-ink",
              )}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}
