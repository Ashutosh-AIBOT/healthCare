import fs from "node:fs";
import path from "node:path";

const appDir = path.join(process.cwd(), "app");
const pagesDir = path.join(process.cwd(), "src", "app");

const targetDir = fs.existsSync(appDir) ? appDir : pagesDir;
if (!fs.existsSync(targetDir)) {
  console.error("Could not find app directory.");
  process.exit(1);
}

const issues: string[] = [];

function walk(dir: string, baseRoute = "") {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    if (entry.isDirectory()) {
      const route = baseRoute ? `${baseRoute}/${entry.name}` : `/${entry.name}`;
      walk(full, route);
    } else if (entry.name === "page.tsx" || entry.name === "page.ts") {
      const content = fs.readFileSync(full, "utf8");
      const relative = path.relative(targetDir, full);
      if (!content.includes("export const metadata") && !content.includes("export const generateMetadata")) {
        issues.push(`Missing metadata export: ${relative}`);
      }
      if (content.includes("robots: { index: false") || content.includes('robots: { index: false')) {
        continue;
      }
      if (!content.includes("robots: { index: true") && !content.includes("robots: { index: true")) {
        issues.push(`Missing robots index in: ${relative}`);
      }
    }
  }
}

walk(targetDir);

if (issues.length > 0) {
  console.log("SEO check found issues:");
  for (const issue of issues) {
    console.log(`  - ${issue}`);
  }
  process.exit(1);
} else {
  console.log("SEO check passed: all pages have metadata and robots directives.");
}
