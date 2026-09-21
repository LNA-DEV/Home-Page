/* L0 — the build as a test.
 *
 * Hugo already refuses to build on an errorf. Treating every WARN line as a
 * failure extends that to the warnf calls and to Hugo's own warnings, which
 * turns the deploy into a gate for free: an unknown `species:`, an empty gallery
 * mount, a template deprecation introduced by a PaperMod bump.
 *
 * It does NOT pass --panicOnWarning — that stops at the first warning, and the
 * report should show all of them at once. deploy.sh's own hugo does pass it,
 * because there the first warning is reason enough to stop.
 *
 * The trade-off is explicit: a warning blocks a deploy. That is the point. The
 * escape hatch for a warning that is genuinely someone else's problem is Hugo's
 * `ignoreLogs` list in hugo.yaml, keyed by the warning's id, so an ignore is
 * visible and reviewable. */

import { test, expect } from "@playwright/test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { REPO } from "../support/site";

const run = promisify(execFile);

/* A cold image cache runs past ten minutes. Slow is not wrong. */
test.describe.configure({ mode: "serial", timeout: 20 * 60_000 });

test("hugo builds without warnings", async ({}, testInfo) => {
  testInfo.setTimeout(20 * 60_000);

  const args = [
    "-e", "production",           // head.html gates opengraph/twitter/JSON-LD on it
    "-b", "http://localhost:1414", // keeps the menu's absolute links on the test server
    "-d", ".test-site",            // public/ stays exclusively the deploy artefact
    "--cleanDestinationDir",
    "--printI18nWarnings",
    "--printPathWarnings",
    "--logLevel", "warn",
  ];

  let stdout = "";
  let stderr = "";
  let code = 0;
  try {
    const r = await run("hugo", args, { cwd: REPO, maxBuffer: 64 * 1024 * 1024 });
    stdout = r.stdout;
    stderr = r.stderr;
  } catch (e: any) {
    stdout = e.stdout ?? "";
    stderr = e.stderr ?? "";
    code = e.code ?? 1;
  }

  const log = `$ hugo ${args.join(" ")}\n\n--- stdout ---\n${stdout}\n--- stderr ---\n${stderr}`;
  await testInfo.attach("hugo.log", { body: log, contentType: "text/plain" });

  const warnings = (stdout + stderr)
    .split("\n")
    .filter((l) => /\bWARN\b/.test(l));

  expect(code, `hugo exited ${code}\n${log}`).toBe(0);
  expect(warnings, `hugo emitted ${warnings.length} warning(s):\n${warnings.join("\n")}`).toEqual([]);
});

test("hugo mod verify", async ({}, testInfo) => {
  const r = await run("hugo", ["mod", "verify"], { cwd: REPO, maxBuffer: 8 * 1024 * 1024 });
  await testInfo.attach("hugo-mod-verify.log", {
    body: r.stdout + r.stderr,
    contentType: "text/plain",
  });
});
