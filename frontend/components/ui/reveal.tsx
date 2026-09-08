"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const delayClass: Record<number, string> = {
  0: "delay-0",
  80: "delay-[80ms]",
  90: "delay-[90ms]",
  100: "delay-[100ms]",
  120: "delay-[120ms]",
  160: "delay-[160ms]",
  180: "delay-[180ms]",
  220: "delay-[220ms]",
};

export function Reveal({
  children,
  className,
  delayMs = 0,
  durationMs = 700,
  distancePx = 16,
}: {
  children: ReactNode;
  className?: string;
  delayMs?: number;
  /** Reveal duration in ms. Default 700 preserves existing behavior. */
  durationMs?: number;
  /** Rise distance in px. Default 16 preserves existing behavior. */
  distancePx?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.14, rootMargin: "0px 0px -6% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const durationClass: Record<number, string> = {
    300: "duration-300",
    400: "duration-[400ms]",
    500: "duration-500",
    700: "duration-700",
  };
  const hiddenClass: Record<number, string> = {
    8: "translate-y-2",
    12: "translate-y-3",
    16: "translate-y-4",
  };
  return (
    <div
      ref={ref}
      className={cn(
        "transition-[opacity,transform] ease-soft will-change-transform",
        durationClass[durationMs] ?? "duration-700",
        delayClass[delayMs] ?? "delay-0",
        visible ? "translate-y-0 opacity-100" : `${hiddenClass[distancePx] ?? "translate-y-4"} opacity-0`,
        className,
      )}
    >
      {children}
    </div>
  );
}
