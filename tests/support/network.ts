/* The network policy, and the mocks that make it liveable.
 *
 * Default: every request to a host other than localhost is ABORTED. The block is
 * itself the assertion the dex map needs — "a species page makes zero
 * third-party requests on load" is what makes it usable over Tor — and it keeps
 * Plausible, the companion API, listmonk and GitHub from ever seeing a test run.
 *
 * A scenario that needs a third party asks for it by name, and gets an answer
 * this file wrote rather than whatever the real service is doing today. */

import type { Page, Route, Request } from "@playwright/test";

export const COMPANION = "https://companion.lna-dev.net";
/* The analytics script sits in extend_head.html, unconditionally, so it is on
   every page of every build — the one third party a page contacts on load. */
export const ANALYTICS = /muninn\.lna-dev\.net/;
export const LISTMONK = "https://listmonk.lna-dev.net";

export type NetworkLog = {
  /** Every request that was not localhost, in order. */
  external: string[];
  /** The analytics script, answered with an empty stub rather than aborted. */
  stubbed: string[];
  /** Those that an allow-list let through to a mock. */
  allowed: string[];
  /** Those that were aborted. */
  blocked: string[];
};

function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return "";
  }
}

export function isLocal(url: string): boolean {
  const h = hostOf(url);
  return h.startsWith("localhost") || h.startsWith("127.0.0.1") || h === "";
}

/** Install the policy. Returns the log, which a test can assert against. */
export async function installNetworkPolicy(
  page: Page,
  opts: { allow?: RegExp[] } = {},
): Promise<NetworkLog> {
  const log: NetworkLog = { external: [], allowed: [], blocked: [], stubbed: [] };
  const allow = opts.allow ?? [];

  await page.route("**/*", async (route: Route, request: Request) => {
    const url = request.url();
    if (isLocal(url)) return route.continue();

    log.external.push(url);

    /* Answered rather than aborted, for one reason: Chromium logs an aborted
       request as a console error and Firefox does not, so blocking the analytics
       script would make the "no console error" scenario pass in one engine and
       fail in the other. An empty script is the same thing as far as the page is
       concerned, and the real service still never sees a test run. */
    if (ANALYTICS.test(url)) {
      log.stubbed.push(url);
      return route.fulfill({ contentType: "application/javascript", body: "" });
    }

    if (allow.some((re) => re.test(url))) {
      log.allowed.push(url);
      return route.fallback(); // a more specific mock route handles it
    }
    log.blocked.push(url);
    return route.abort();
  });

  return log;
}

/** The companion API: like counts and the native like toggle.
 *  `posted` records the writes, so a test can assert the page posted once. */
export async function mockCompanion(page: Page, opts: { likes?: number } = {}) {
  const likes = opts.likes ?? 7;
  const posted: { method: string; url: string }[] = [];

  await page.route(`${COMPANION}/api/interactions/native/*/status*`, (route) =>
    route.fulfill({ json: { has_liked: false } }),
  );

  await page.route(`${COMPANION}/api/interactions/native/*/like`, (route) => {
    posted.push({ method: route.request().method(), url: route.request().url() });
    return route.fulfill({ json: { ok: true } });
  });

  await page.route(`${COMPANION}/api/interactions/post/all/*`, (route) =>
    route.fulfill({ json: [{ platform: "native", likes }] }),
  );

  await page.route(`${COMPANION}/api/trips*`, (route) => route.fulfill({ json: [] }));

  return { posted };
}

/** listmonk's public subscription endpoint. */
export async function mockListmonk(page: Page, opts: { fail?: boolean } = {}) {
  const posted: string[] = [];
  await page.route(`${LISTMONK}/api/public/subscription*`, (route) => {
    posted.push(route.request().postData() ?? "");
    return opts.fail
      ? route.fulfill({ status: 500, json: { message: "nope" } })
      : route.fulfill({ json: { data: true } });
  });
  return { posted };
}

/** The two the "detailed map" button is allowed to reach, and nothing else. */
export async function mockDetailedMap(page: Page) {
  const hit: string[] = [];
  await page.route(/tile\.openstreetmap\.org/, (route) => {
    hit.push(route.request().url());
    /* A 1×1 transparent PNG: Leaflet only needs the request to succeed. */
    return route.fulfill({
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "base64",
      ),
    });
  });
  await page.route(/api\.gbif\.org/, (route) => {
    hit.push(route.request().url());
    return route.fulfill({
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "base64",
      ),
    });
  });
  return { hit };
}

export const ALLOW_COMPANION = [/companion\.lna-dev\.net/];
export const ALLOW_LISTMONK = [/listmonk\.lna-dev\.net/];
export const ALLOW_MAP_TILES = [/tile\.openstreetmap\.org/, /api\.gbif\.org/];
