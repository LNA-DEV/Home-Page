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
import { createHash } from "node:crypto";

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

/** The number the mocked ALTCHA challenge hides; small, so a test solves it fast. */
export const ALTCHA_NUMBER = 1234;

/** listmonk's subscription form and its ALTCHA challenge.
 *
 *  `captcha: false` (the default) answers the challenge with 404, which is what
 *  listmonk does while ALTCHA is switched off. `captcha: true` serves a challenge
 *  made the way altcha-lib-go makes it — the salt carries `expires` and ends in
 *  `&`, the challenge is SHA-256(salt + number) in hex — with a fake signature,
 *  since the test checks what the page sends back, not the HMAC. */
export async function mockListmonk(page: Page, opts: { fail?: boolean; captcha?: boolean } = {}) {
  const posted: string[] = [];
  const challenges: string[] = [];
  const expires = Math.floor(Date.now() / 1000) + 300;
  const salt = `0123456789abcdef01234567?expires=${expires}&`;
  const challenge = {
    algorithm: "SHA-256",
    challenge: createHash("sha256").update(salt + ALTCHA_NUMBER).digest("hex"),
    maxNumber: 5000,
    salt,
    signature: "test-signature",
  };

  await page.route(`${LISTMONK}/api/public/captcha/altcha*`, (route) => {
    challenges.push(route.request().url());
    return opts.captcha
      ? route.fulfill({ json: challenge })
      : route.fulfill({ status: 404, json: { message: "captcha not enabled" } });
  });
  await page.route(`${LISTMONK}/subscription/form*`, (route) => {
    if (route.request().method() !== "POST") return route.abort();
    posted.push(route.request().postData() ?? "");
    return opts.fail
      ? route.fulfill({ status: 500, contentType: "text/html", body: "<p>nope</p>" })
      : route.fulfill({ contentType: "text/html", body: "<p>ok</p>" });
  });
  return { posted, challenges, challenge };
}

/** A transparent 1×1 PNG: a raster tile layer only needs the request to succeed. */
const PNG_1X1 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg==",
  "base64",
);

/** The basemap version the TileJSON mock points at. */
export const BASEMAP_VERSION = "20261005";

/** Every map tile the site asks for comes from the companion
 *  (docs/concepts/self-hosted-maps.md): the basemap's TileJSON and its vector
 *  tiles, and GBIF's density overlay through the companion's proxy. `hit`
 *  records each request, so a test can assert what a map actually used.
 *
 *  A vector tile is answered with an empty body — a valid, empty tile, which
 *  MapLibre draws as nothing. Whether anything was *drawn* is not this mock's
 *  question; that the page asked the companion, and nobody else, is. */
export async function mockMapTiles(page: Page) {
  const hit: string[] = [];
  await page.route(`${COMPANION}/api/tiles/basemap.json`, (route) => {
    hit.push(route.request().url());
    return route.fulfill({
      json: {
        tilejson: "3.0.0",
        name: "Protomaps Basemap",
        tiles: [`${COMPANION}/api/tiles/basemap/${BASEMAP_VERSION}/{z}/{x}/{y}.mvt`],
        minzoom: 0,
        maxzoom: 15,
        bounds: [-180, -85.0511287, 180, 85.0511287],
        vector_layers: [],
      },
    });
  });
  await page.route(`${COMPANION}/api/tiles/basemap/**`, (route) => {
    hit.push(route.request().url());
    return route.fulfill({ contentType: "application/x-protobuf", body: Buffer.alloc(0) });
  });
  await page.route(`${COMPANION}/api/tiles/gbif/**`, (route) => {
    hit.push(route.request().url());
    return route.fulfill({ contentType: "image/png", body: PNG_1X1 });
  });
  return { hit };
}

export const ALLOW_COMPANION = [/companion\.lna-dev\.net/];
export const ALLOW_LISTMONK = [/listmonk\.lna-dev\.net/];
