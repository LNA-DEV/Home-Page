#!/usr/bin/env node
/* Regenerate tests/golden/published-urls.txt after an INTENTIONAL URL change.
 *
 * The list is append-only by construction: this script unions the current build
 * with what is already committed and never drops a line. A URL leaves the list
 * only by a hand edit, in a commit that also adds its redirect — which is the
 * rule CLAUDE.md states for the gallery and for RSS and that nothing could check
 * before. */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { collectPublishedPaths } from "./collect.mjs";

const REPO = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));
const SITE_DIR = path.resolve(REPO, process.env.SITE_DIR ?? ".test-site");
const SITE_BASE = process.env.SITE_BASE ?? "http://localhost:1414";
const LIST = path.join(REPO, "tests/golden/published-urls.txt");

if (!fs.existsSync(path.join(SITE_DIR, "sitemap.xml"))) {
  console.error(`No sitemap under ${SITE_DIR} — run \`npx playwright test --project build\` first.`);
  process.exit(1);
}

const existing = fs.existsSync(LIST)
  ? fs.readFileSync(LIST, "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"))
  : [];

const current = collectPublishedPaths(SITE_DIR, SITE_BASE);
const merged = [...new Set([...existing, ...current])].sort();
const added = merged.filter((u) => !existing.includes(u));

const header = [
  "# Every URL this site has ever published, path only: the <loc> of every",
  "# sitemap entry and the <link> of every feed item.",
  "#",
  "# The test is not \"this list is unchanged\" but \"every URL on it still",
  "# resolves to a page or to an alias\". Regenerate with `npm run golden:update`,",
  "# which only ever adds. Removing a line is a deliberate retirement and belongs",
  "# in the same commit as the redirect that keeps the old URL alive.",
  "",
];
fs.writeFileSync(LIST, header.join("\n") + merged.join("\n") + "\n");
console.log(`${merged.length} URLs (${added.length} new, ${existing.length} kept)`);
for (const u of added.slice(0, 20)) console.log(`  + ${u}`);
if (added.length > 20) console.log(`  … and ${added.length - 20} more`);
