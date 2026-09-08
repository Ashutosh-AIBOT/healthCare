"use client";

const ORDERED_KEYS = [
  "calories",
  "protein",
  "carbs",
  "fat",
  "fiber",
  "sugar",
  "calcium",
  "iron",
  "vitamin_c",
  "vitamin_d",
  "vitamin_b12",
  "magnesium",
  "potassium",
  "zinc",
];

function prettyKey(key: string): string {
  return key
    .replace(/_per_100g$/i, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function NutritionTable({
  nutrition,
}: {
  nutrition: Record<string, number | string> | null;
}) {
  if (!nutrition || Object.keys(nutrition).length === 0) {
    return (
      <p className="text-sm text-muted">
        Nutrition values are being curated for this item.
      </p>
    );
  }
  const keys = [
    ...ORDERED_KEYS.filter((k) =>
      Object.keys(nutrition).some(
        (nk) => nk.toLowerCase().replace(/[^a-z]/g, "") === k.replace(/[^a-z]/g, ""),
      ),
    ),
    ...Object.keys(nutrition).filter(
      (nk) =>
        !ORDERED_KEYS.some(
          (k) => nk.toLowerCase().replace(/[^a-z]/g, "") === k.replace(/[^a-z]/g, ""),
        ),
    ),
  ];
  const norm = (want: string): string | null => {
    const hit = Object.keys(nutrition).find(
      (nk) => nk.toLowerCase().replace(/[^a-z]/g, "") === want.replace(/[^a-z]/g, ""),
    );
    return hit ?? null;
  };
  return (
    <div className="overflow-hidden rounded-2xl border border-line">
      <table className="w-full text-sm">
        <caption className="bg-mist/50 px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted">
          Per 100 g (approx)
        </caption>
        <tbody>
          {keys.map((k) => {
            const real = norm(k) ?? k;
            const v = nutrition[real];
            return (
              <tr key={k} className="border-t border-line/60 first:border-t-0">
                <th
                  scope="row"
                  className="px-4 py-2 text-left font-medium text-muted"
                >
                  {prettyKey(k)}
                </th>
                <td className="tabular px-4 py-2 text-right font-semibold text-ink">
                  {String(v)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
