/* L1 — the Python scripts, bridged into the one report.
 *
 * stdlib `unittest`, no pytest: the scripts are stdlib-only on purpose — any
 * machine with python3 can add a photo — and their tests keep that property.
 *
 * One Playwright test per module rather than one for the whole suite, so the
 * report says which toolchain broke and carries that module's output as an
 * attachment. No dependency on `build`; this runs alongside it and needs no
 * photos, no exiftool and no network. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { REPO } from "../support/site";

const run = promisify(execFile);
const PY_DIR = path.join(REPO, "tests", "py");

const modules = fs
  .readdirSync(PY_DIR)
  .filter((f) => f.startsWith("test_") && f.endsWith(".py"))
  .map((f) => f.replace(/\.py$/, ""))
  .sort();

test("there are Python tests to run", () => {
  expect(modules.length, `no test_*.py under ${PY_DIR}`).toBeGreaterThan(0);
});

for (const mod of modules) {
  test(`python: ${mod}`, async ({}, testInfo) => {
    let out = "";
    let failed = false;
    try {
      const r = await run("python3", ["-m", "unittest", "-v", mod], {
        cwd: PY_DIR,
        maxBuffer: 16 * 1024 * 1024,
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
      });
      out = r.stdout + r.stderr;
    } catch (e: any) {
      out = (e.stdout ?? "") + (e.stderr ?? "");
      failed = true;
    }
    await testInfo.attach(`${mod}.txt`, { body: out, contentType: "text/plain" });
    expect(failed, out).toBe(false);
  });
}
