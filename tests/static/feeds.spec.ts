/* L2 — feeds, sitemap and security.txt.
 *
 * `fix rss` appears twice in the last thirty fix commits, plus `fix gallery link
 * in feed`, `Fix alias`, `Fix categories` and a `security.txt` whose Expires had
 * been four months in the past for nobody knows how long. All of it is a
 * property of a file on disk. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import {
  SITE_BASE, SITE_DIR, LANGS, xmlFiles, readSiteFile, servedPaths, sitePath,
} from "../support/site";

const run = promisify(execFile);

test("every XML file is well-formed", async () => {
  const files = xmlFiles().map((f) => path.join(SITE_DIR, f));
  expect(files.length, "no XML in the build at all").toBeGreaterThan(10);
  /* xmllint is in libxml2 and on every machine that has ever built this site;
     a Node XML parser would be a third dependency for one assertion. */
  for (let i = 0; i < files.length; i += 50) {
    await run("xmllint", ["--noout", ...files.slice(i, i + 50)]);
  }
});

test.describe("feeds", () => {
  const feeds = () => xmlFiles().filter((f) => path.basename(f) === "index.xml");

  test("there is a feed, and every item link is absolute and resolves", () => {
    const served = servedPaths();
    const bad: string[] = [];
    expect(feeds().length, "no index.xml anywhere").toBeGreaterThan(0);

    for (const f of feeds()) {
      const xml = readSiteFile(f);
      for (const m of xml.matchAll(/<link>([^<]*)<\/link>/g)) {
        const url = m[1].trim();
        if (!url) continue;
        if (!/^https?:\/\//.test(url)) {
          bad.push(`${f}: relative <link> ${url} — a feed reader has no base to resolve it against`);
          continue;
        }
        if (!url.startsWith(SITE_BASE)) continue;
        const p = decodeURIComponent(new URL(url).pathname);
        if (!served.has(p) && !served.has(p + "/") && !served.has(p + "index.html")) {
          bad.push(`${f}: <link> ${url} resolves to nothing`);
        }
      }
    }
    expect(bad.slice(0, 20), `${bad.length} problem(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("every URL inside content:encoded is absolute", () => {
    /* A feed reader renders the body on its own origin; a relative src there is
       a broken image in every client. */
    const bad: string[] = [];
    for (const f of feeds()) {
      const xml = readSiteFile(f);
      for (const block of xml.matchAll(/<content:encoded>([\s\S]*?)<\/content:encoded>/g)) {
        for (const m of block[1].matchAll(/(?:src|href)=(?:"|&quot;|&#34;)([^"&]+)/g)) {
          const u = m[1];
          if (/^(https?:)?\/\//.test(u) || /^(mailto|data|tel):/.test(u) || u.startsWith("#")) continue;
          bad.push(`${f}: ${u}`);
        }
      }
    }
    expect(bad.slice(0, 20), `${bad.length} relative URL(s) in feed bodies\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });
});

test.describe("sitemap", () => {
  test("every listed URL exists", () => {
    const served = servedPaths();
    const bad: string[] = [];
    for (const lang of LANGS) {
      const xml = readSiteFile(path.join(lang, "sitemap.xml"));
      for (const m of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) {
        const url = m[1].trim();
        if (!url.startsWith(SITE_BASE)) continue;
        const p = decodeURIComponent(new URL(url).pathname);
        if (!served.has(p) && !served.has(p + "/") && !served.has(p + "index.html")) bad.push(`${lang}: ${url}`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} sitemap URL(s) that do not exist\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("no page is listed with priority 0", () => {
    /* A zero priority is how an adapter page used to announce itself as not
       worth crawling — it means the page should not have been listed at all. */
    const bad: string[] = [];
    for (const lang of LANGS) {
      const xml = readSiteFile(path.join(lang, "sitemap.xml"));
      for (const m of xml.matchAll(/<url>([\s\S]*?)<\/url>/g)) {
        if (/<priority>\s*0(?:\.0+)?\s*<\/priority>/.test(m[1])) {
          bad.push(`${lang}: ${m[1].match(/<loc>([^<]+)<\/loc>/)?.[1]}`);
        }
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("redirect pages are not listed", () => {
    const bad: string[] = [];
    for (const lang of LANGS) {
      const xml = readSiteFile(path.join(lang, "sitemap.xml"));
      for (const m of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) {
        const p = new URL(m[1]).pathname;
        const file = sitePath(decodeURIComponent(p).replace(/^\//, "") + "index.html");
        if (fs.existsSync(file) && /http-equiv="refresh"/.test(fs.readFileSync(file, "utf8"))) {
          bad.push(`${lang}: ${m[1]} is an alias`);
        }
      }
    }
    expect(bad.slice(0, 10), `${bad.length} alias page(s) in the sitemap\n${bad.slice(0, 10).join("\n")}`).toEqual([]);
  });
});

test.describe("security.txt", () => {
  const read = () => readSiteFile(path.join(".well-known", "security.txt"));

  test("it is generated, present and at the domain root", () => {
    /* The output format's `path` is ../.well-known because path resolves
       relative to the language directory. Get that wrong and the file lands
       under /en/. */
    expect(fs.existsSync(sitePath(".well-known", "security.txt")), "not at the domain root").toBe(true);
    for (const lang of LANGS) {
      expect(fs.existsSync(sitePath(lang, ".well-known", "security.txt")), `${lang} wrote its own copy — securitytxt belongs in languages.en.outputs.home only`).toBe(false);
    }
  });

  test("Expires is in the future and less than a year out", () => {
    const m = read().match(/^Expires:\s*(.+)$/m);
    expect(m, "no Expires field — RFC 9116 requires one").toBeTruthy();
    const expires = new Date(m![1].trim());
    const now = new Date();
    expect(expires.getTime(), `Expires ${m![1]} is in the past`).toBeGreaterThan(now.getTime());
    const year = 366 * 24 * 3600 * 1000;
    expect(expires.getTime() - now.getTime(), "Expires is more than a year out; RFC 9116 recommends less").toBeLessThan(year);
  });

  test("Canonical follows the base URL of the build", () => {
    /* absURL, so the Tor build emits the onion address instead of the clearnet
       one. */
    const m = read().match(/^Canonical:\s*(.+)$/m);
    expect(m, "no Canonical field").toBeTruthy();
    expect(m![1].trim()).toBe(`${SITE_BASE}/.well-known/security.txt`);
  });
});
