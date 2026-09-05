import Link from "next/link";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

const icons: Record<string, ReactNode> = {
  doctors: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0h.5a2.5 2.5 0 0 0 0-5H4Z" />
      <path d="M15.5 11.5a5 5 0 0 0-5-5v-1h5v1Z" />
      <path d="M14.5 11.5a5 5 0 0 1 5-5v1h-5v-1Z" />
      <path d="M20.5 6.5H18v5h5v-2a2.5 2.5 0 0 0-2.5-2.5Z" />
      <path d="M14.5 11.5v5a5 5 0 0 0 5 5h-2a3 3 0 0 1-3-3v-2.5a2.5 2.5 0 0 0-2.5-2.5H8v-1a5 5 0 0 1 5-5h1.5Z" />
      <path d="M6.5 11.5v5a5 5 0 0 0 5 5h.5a2.5 2.5 0 0 0 0-5H6.5Z" />
      <path d="M6.5 11.5a5 5 0 0 1 5-5h.5a2.5 2.5 0 0 1 0 5H11v5a5 5 0 0 1-5 5h-.5a2.5 2.5 0 0 1 0-5H6.5Z" />
    </svg>
  ),
  labs: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  ),
  pharmacy: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M10.5 20.5 10.5 10.5" />
      <path d="M13.5 20.5 13.5 10.5" />
      <path d="M16.5 20.5 16.5 10.5" />
      <path d="M7.5 10.5 7.5 20.5" />
      <path d="M3 7.5 21 7.5" />
      <path d="M10 13.5 10 16.5" />
      <path d="M13.5 13.5 13.5 16.5" />
      <path d="M7.5 16.5 7.5 13.5" />
    </svg>
  ),
  ambulance: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M10 17h4V5H2v12h3" />
      <path d="M20 17h2v-3.34a4 4 0 0 0-1.17-2.83L19 9h-5v8h1" />
      <circle cx="7.5" cy="17.5" r="2.5" />
      <circle cx="16.5" cy="17.5" r="2.5" />
    </svg>
  ),
};

const colorStyles: Record<string, string> = {
  primary: "bg-primary text-primary-foreground",
  lime: "bg-primary text-primary-foreground",
  blush: "bg-primary text-primary-foreground",
  apricot: "bg-primary text-primary-foreground",
};

export function ServiceCard({
  title,
  description,
  icon,
  color = "primary",
  className,
  href,
}: {
  title: string;
  description?: string;
  icon: keyof typeof icons;
  color?: keyof typeof colorStyles;
  className?: string;
  href?: string;
}) {
  const bg = colorStyles[color] || colorStyles.primary;

  const Card = href ? Link : "div";
  const cardProps = href ? { href } : {};

  return (
    <Card
      {...cardProps}
      className={cn(
         "flex flex-col gap-3 rounded-[1.75rem] bg-surface p-5 shadow-card transition-transform duration-300 ease-soft hover:-translate-y-0.5 hover:shadow-lift",
        className,
      )}
    >
      <div className={cn("inline-flex h-10 w-10 items-center justify-center rounded-xl", bg)}>
        {icons[icon] || icons.doctors}
      </div>
      <div>
        <h3 className="font-semibold text-ink">{title}</h3>
        {description ? <p className="mt-1 text-xs text-muted">{description}</p> : null}
      </div>
    </Card>
  );
}
