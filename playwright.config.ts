import { defineConfig, devices } from "@playwright/test";

/* One runner for all four layers of docs/concepts/testing.md.
 *
 * The build and the Python suite are Playwright *projects* rather than a shell
 * script chaining steps, so a failed build is one red test with Hugo's log
 * attached and everything downstream is skipped rather than forty red tests.
 *
 *   python ──────────────────────────────────────────┐
 *   build ──┬── static                               ├── one HTML report
 *           ├── firefox   chromium   webkit          │
 *           └── mobile-chrome   mobile-safari  ──────┘
 */

/* Where the site under test lives, and the base URL it was built with.
 *
 * Default: .test-site/, built by the `build` project at http://localhost:1414.
 * deploy.sh overrides both to run the static checks over the very files rsync is
 * about to ship (SITE_DIR=public SITE_BASE=https://lna-dev.net) — and when
 * SITE_DIR is set from outside, `static` drops its dependency on `build`, or
 * Playwright would helpfully rebuild .test-site/ first. */
const SITE_DIR = process.env.SITE_DIR ?? ".test-site";
const SITE_BASE = process.env.SITE_BASE ?? "http://localhost:1414";
const EXTERNAL_SITE = Boolean(process.env.SITE_DIR);

const PORT = 1414;

/* WebKit — and with it mobile-safari — is opt-in, because it does not run on
 * this machine as shipped. Playwright's Linux WebKit build links ICU 74 and
 * libjpeg.so.8; Fedora has ICU 77 and libjpeg.so.62, and `playwright
 * install-deps` only knows apt. The two ways to run it:
 *
 *   WEBKIT=1 npm test                     once the libraries are there
 *   podman run --rm --network=host \
 *     -v "$PWD":/w -w /w \
 *     mcr.microsoft.com/playwright:v1.63.0-noble \
 *     npx playwright test --project webkit
 *
 * Left out of the default run rather than left failing: a suite that is red
 * every time teaches people to ignore red. Firefox, Chromium and mobile-chrome
 * are the default matrix; every scenario runs in all three. */
const WEBKIT = Boolean(process.env.WEBKIT);

export default defineConfig({
  testDir: "tests",
  /* A cold image cache is slow, not wrong — the build test raises its own
     timeout past this one. */
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  /* Flakiness should be seen rather than hidden. Revisit when there is data. */
  retries: 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ["list"],
    ["html", { open: "on-failure", outputFolder: "playwright-report" }],
  ],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  /* stdlib, already on the machine, serves index.html for directories and
     decodes percent-escapes. A directory listing answers 200 before the build
     exists, so the server is up in a second and never in the way. */
  webServer: {
    /* http.server logs every request to stderr; with 4,600 pages under test
       that buries the report's own output. Errors that matter surface as failed
       requests in the tests themselves. */
    command: `mkdir -p ${SITE_DIR} && python3 -m http.server ${PORT} -d ${SITE_DIR} 2>/dev/null`,
    url: `http://localhost:${PORT}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    stdout: "ignore",
    stderr: "pipe",
  },

  projects: [
    {
      name: "python",
      testMatch: /tests\/python\/.*\.spec\.ts/,
    },
    {
      name: "build",
      testMatch: /tests\/build\/.*\.spec\.ts/,
      /* Never rebuild something the caller handed us. */
      testIgnore: EXTERNAL_SITE ? /.*/ : undefined,
    },
    {
      name: "static",
      testMatch: /tests\/static\/.*\.spec\.ts/,
      dependencies: EXTERNAL_SITE ? [] : ["build"],
    },

    {
      /* Listed first of the browsers so its failures lead the report: Firefox is
         the primary browser and a failure there is the one to look at first. */
      name: "firefox",
      testMatch: /tests\/e2e\/.*\.spec\.ts/,
      use: { ...devices["Desktop Firefox"], viewport: { width: 1280, height: 800 } },
      dependencies: EXTERNAL_SITE ? [] : ["build"],
    },
    {
      name: "chromium",
      testMatch: /tests\/e2e\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
      dependencies: EXTERNAL_SITE ? [] : ["build"],
    },
    /* WebKit is opt-in on this machine — see WEBKIT above. */
    ...(WEBKIT
      ? [
          {
            name: "webkit",
            testMatch: /tests\/e2e\/.*\.spec\.ts/,
            use: { ...devices["Desktop Safari"], viewport: { width: 1280, height: 800 } },
            dependencies: EXTERNAL_SITE ? [] : ["build"],
          },
        ]
      : []),
    {
      /* Firefox has no mobile emulation in Playwright, which is why both mobile
         projects run on the other two engines — also the honest choice, since
         the phones in question run Chrome and Safari. */
      name: "mobile-chrome",
      testMatch: /tests\/e2e\/.*\.spec\.ts/,
      grep: /@mobile/,
      use: { ...devices["Pixel 7"] },
      dependencies: EXTERNAL_SITE ? [] : ["build"],
    },
    ...(WEBKIT
      ? [
          {
            name: "mobile-safari",
            testMatch: /tests\/e2e\/.*\.spec\.ts/,
            grep: /@mobile/,
            use: { ...devices["iPhone 14"] },
            dependencies: EXTERNAL_SITE ? [] : ["build"],
          },
        ]
      : []),
  ],

  metadata: { siteDir: SITE_DIR, siteBase: SITE_BASE },
});

export { SITE_DIR, SITE_BASE, PORT };
