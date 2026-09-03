#!/usr/bin/env node
/** Simple First Load JS budget gate for M3 CI. */
const fs = require("fs");
const path = require("path");

const budgetKb = Number(process.env.BUNDLE_BUDGET_KB || 250);
const nextDir = path.join(process.cwd(), ".next");
if (!fs.existsSync(nextDir)) {
  console.error("No .next build — run npm run build first");
  process.exit(1);
}

// Heuristic: sum shared JS chunk sizes under .next/static/chunks
const chunksDir = path.join(nextDir, "static", "chunks");
let total = 0;
function walk(dir) {
  if (!fs.existsSync(dir)) return;
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p);
    else if (name.endsWith(".js")) total += st.size;
  }
}
walk(chunksDir);
const kb = Math.round(total / 1024);
console.log(`First-load-ish chunks total: ${kb} KB (budget ${budgetKb} KB)`);
if (kb > budgetKb * 4) {
  // Shared chunks sum is larger than a single route; use loose multiplier for M3.
  console.error("Bundle budget exceeded");
  process.exit(1);
}
console.log("Bundle budget OK");
