import { LearnShell } from "./_components/learn-shell";

export default function LearnRootLayout({ children }: { children: React.ReactNode }) {
  return <LearnShell>{children}</LearnShell>;
}
