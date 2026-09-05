import { cn } from "@/lib/utils";

const points = [
  { x: 0, y: 28 },
  { x: 32, y: 20 },
  { x: 64, y: 32 },
  { x: 96, y: 14 },
  { x: 128, y: 18 },
  { x: 160, y: 10 },
  { x: 192, y: 22 },
  { x: 224, y: 8 },
  { x: 256, y: 16 },
  { x: 288, y: 4 },
];

const viewBoxW = 288;
const viewBoxH = 40;

const path = points
  .map((p, i) => {
    const x = p.x;
    const y = viewBoxH - p.y;
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  })
  .join(" ");

const areaPath = `${path} L ${viewBoxW} ${viewBoxH} L 0 ${viewBoxH} Z`;

const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function ActivityChart({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-[1.75rem] bg-surface p-5 shadow-card", className)}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-ink">Current Activity</h3>
          <p className="mt-0.5 text-xs text-muted">Weekly overview</p>
        </div>
        <span className="rounded-full bg-primary-soft px-2.5 py-1 text-[11px] font-semibold text-primary">
          +12%
        </span>
      </div>
      <div className="mt-4">
        <svg viewBox={`0 0 ${viewBoxW} ${viewBoxH}`} className="h-32 w-full" aria-label="Activity line chart">
          <defs>
            <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.25" />
              <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill="url(#chartGrad)" />
          <path
            d={path}
            fill="none"
            stroke="var(--color-primary)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {points.map((p, i) => (
            <circle key={i} cx={p.x} cy={viewBoxH - p.y} r="3" fill="white" stroke="var(--color-primary)" strokeWidth="2" />
          ))}
        </svg>
        <div className="mt-3 flex items-center justify-between text-[11px] text-muted">
          {labels.map((l) => (
            <span key={l}>{l}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
