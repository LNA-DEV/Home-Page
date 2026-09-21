/* L2 — the build is reproducible. @slow
 *
 * Two builds of the same tree must produce byte-identical HTML. It was not true
 * when the concept was written: layouts/shortcodes/map.html drew its element id
 * from math.Rand, so every build of a page with a map differed and no diff
 * against a previous build meant anything.
 *
 * Tagged @slow because it runs a second full build (~15 s warm) into its own
 * destination. `npm run test:quick` skips it. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { REPO, SITE_DIR, htmlFiles } from "../support/site";

const run = promisify(execFile);
const VERIFY = path.join(REPO, ".test-site-verify");

function sha(file: string): string {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

test("two builds of the same tree produce identical HTML @slow", async ({}, testInfo) => {
  testInfo.setTimeout(20 * 60_000);
  test.skip(
    path.resolve(SITE_DIR) !== path.join(REPO, ".test-site"),
    "only meaningful against a build this suite made itself",
  );

  await run(
    "hugo",
    [
      "-e", "production",
      "-b", "http://localhost:1414",
      "-d", ".test-site-verify",
      "--cleanDestinationDir",
      "--logLevel", "warn",
    ],
    { cwd: REPO, maxBuffer: 64 * 1024 * 1024 },
  );

  try {
    const differing: string[] = [];
    const missing: string[] = [];
    for (const rel of htmlFiles()) {
      const b = path.join(VERIFY, rel);
      if (!fs.existsSync(b)) {
        missing.push(rel);
        continue;
      }
      if (sha(path.join(SITE_DIR, rel)) !== sha(b)) differing.push(rel);
    }
    expect(missing.slice(0, 10), `${missing.length} page(s) in the first build only`).toEqual([]);
    expect(
      differing.slice(0, 10),
      `${differing.length} page(s) differ between two builds of the same tree — something in a template is not a function of the input\n${differing.slice(0, 10).join("\n")}`,
    ).toEqual([]);
  } finally {
    fs.rmSync(VERIFY, { recursive: true, force: true });
  }
});
