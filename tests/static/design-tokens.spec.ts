/* Design tokens — docs/concepts/design-system.md §9.

   The ratchet: per file and category, the number of literal values that
   should be a token (tests/support/css-literals.mjs says what counts) must
   equal tests/golden/css-literals.json. More is a regression; fewer means the
   golden is stale and `npm run tokens:ratchet` should lock the gain in, in the
   same commit. A source test like image-urls.spec.ts: it reads the repo, not
   the build. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { REPO } from "../support/site";
// @ts-ignore — plain ESM shared with the update script
import { countAll, CATEGORIES, TOKENS_FILE } from "../support/css-literals.mjs";

const GOLDEN = path.join(REPO, "tests/golden/css-literals.json");

test.describe("design tokens", () => {
  test("no file gains a literal value, and no gain goes unrecorded", () => {
    const golden: Record<string, Record<string, number>> = JSON.parse(fs.readFileSync(GOLDEN, "utf8"));
    const now: Record<string, Record<string, number>> = countAll(REPO);
    const worse: string[] = [];
    const better: string[] = [];
    for (const file of new Set([...Object.keys(golden), ...Object.keys(now)])) {
      for (const k of CATEGORIES as string[]) {
        const was = golden[file]?.[k] ?? 0;
        const is = now[file]?.[k] ?? 0;
        if (is > was) worse.push(`${file}: ${k} ${was} → ${is}`);
        if (is < was) better.push(`${file}: ${k} ${was} → ${is}`);
      }
    }
    expect(worse, `literal values where a token belongs (use assets/css/core/theme-vars.css):\n${worse.join("\n")}`).toEqual([]);
    expect(better, `fewer literals than recorded — run \`npm run tokens:ratchet\` and commit tests/golden/css-literals.json:\n${better.join("\n")}`).toEqual([]);
  });

  test("every colour in the tokens file is written once, as light-dark() or deliberately theme-free", () => {
    const src = fs.readFileSync(path.join(REPO, TOKENS_FILE), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    /* Only the main :root block — the @supports fallback for old browsers
       necessarily restates plain values. */
    const main = src.split("@supports")[0];
    const seen = new Map<string, number>();
    for (const m of main.matchAll(/(--[a-z0-9-]+)\s*:/g)) seen.set(m[1], (seen.get(m[1]) ?? 0) + 1);
    const twice = [...seen].filter(([, n]) => n > 1).map(([k]) => k);
    expect(twice, "a token defined twice in the tokens file").toEqual([]);
    /* No [data-theme] or prefers-color-scheme block may redefine a token: one
       definition per token is the point of light-dark(). */
    const outsideRoot = main.replace(/:root\s*\{[\s\S]*?\n\}/, "");
    expect(outsideRoot.match(/--[a-z0-9-]+\s*:/g) ?? [], "token redefined outside the :root block").toEqual([]);
  });
});
