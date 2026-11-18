/* The design-token ratchet's counter — docs/concepts/design-system.md §9.

   Counts, per source file, the values that should have been a token from
   assets/css/core/theme-vars.css. Shared by tests/static/design-tokens.spec.ts
   and `npm run tokens:ratchet`, which rewrites tests/golden/css-literals.json.

   Categories:
     colour      hex, rgb()/rgba()/hsl()/hsla() or a named colour
     spacing     a px/rem/em length in margin*, padding*, gap, row-gap, column-gap
     fontSize    a px/rem length in font-size (em and % are relative, allowed)
     radius      a px/rem length in border-*radius (% allowed)
     shadow      a box-shadow / text-shadow / drop-shadow that carries a colour literal
     breakpoint  a @media width outside the set, or written as min-/max-width

   Never counted: 0, auto, %, vw/vh/ch, var(), inherit/currentColor/transparent,
   and 1–2px hairlines. Plain Node, no dependencies: the spec imports it, and so
   does tests/golden/update-css-literals.mjs. */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

export const TOKENS_FILE = "assets/css/core/theme-vars.css";
export const CATEGORIES = ["colour", "spacing", "fontSize", "radius", "shadow", "breakpoint"];
/* 480 · 640 · 768 · 900 · 1100, and 700 for PhotoSwipe — §6 */
export const BREAKPOINTS = [480, 640, 700, 768, 900, 1100];

const SKIP_DIRS = ["assets/css/photoswipe", "assets/js/packages", "static", "node_modules"];

function walk(dir, repo, out) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const rel = relative(repo, full).split(sep).join("/");
    if (SKIP_DIRS.some((d) => rel === d || rel.startsWith(d + "/"))) continue;
    if (statSync(full).isDirectory()) walk(full, repo, out);
    else out.push(rel);
  }
  return out;
}

/** Every file the ratchet reads, repo-relative, sorted. */
export function sourceFiles(repo) {
  const css = walk(join(repo, "assets/css"), repo, []).filter((f) => /\.(css|scss)$/.test(f) && f !== TOKENS_FILE);
  const js = walk(join(repo, "assets/js"), repo, []).filter((f) => f.endsWith(".js"));
  const html = walk(join(repo, "layouts"), repo, []).filter((f) => f.endsWith(".html"));
  return [...css, ...js, ...html].sort();
}

const NAMED = "white|black|red|green|blue|gray|grey|silver|orange|yellow|purple|pink|brown|navy|teal|maroon|olive|lime|aqua|fuchsia|gold|crimson|tomato|coral";
const COLOUR_PROPS = /^(color|background(-color)?|border(-(top|right|bottom|left|block|inline)(-(start|end))?)?(-color)?|outline(-color)?|fill|stroke|text-decoration(-color)?|caret-color|accent-color|column-rule(-color)?|box-shadow|text-shadow|filter|stop-color|flood-color)$/;
const HEX = /#[0-9a-fA-F]{3,8}\b/g;
const FUNC = /\b(?:rgba?|hsla?)\(/g;
const NAMED_RE = new RegExp(`(^|[\\s,(])(${NAMED})(?=$|[\\s,)!;])`, "gi");
const LENGTH = /(^|[\s(,*/+-])(-?\d*\.?\d+)(px|rem|em)\b/g;

function stripCssComments(src, scss) {
  let s = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "));
  if (scss) s = s.replace(/(^|[^:"'])\/\/[^\n]*/g, (m, p) => p + " ".repeat(m.length - p.length));
  return s;
}

function lengths(value, { allowHairline, allowEm }) {
  let n = 0;
  for (const m of value.matchAll(LENGTH)) {
    const num = Math.abs(parseFloat(m[2]));
    const unit = m[3];
    if (num === 0) continue;
    if (allowEm && unit === "em") continue;
    if (allowHairline && unit === "px" && num <= 2) continue;
    n++;
  }
  return n;
}

function colours(value) {
  const hex = (value.match(HEX) || []).length;
  const func = (value.match(FUNC) || []).length;
  const named = (value.match(NAMED_RE) || []).length;
  return hex + func + named;
}

function countCss(src, scss) {
  const c = Object.fromEntries(CATEGORIES.map((k) => [k, 0]));
  const s = stripCssComments(src, scss);

  for (const m of s.matchAll(/@media\b([^{]*)\{/g)) {
    const q = m[1];
    for (const f of q.matchAll(/\((min|max)-width\s*:\s*([\d.]+)(px|em|rem)\s*\)/g)) c.breakpoint++;
    for (const f of q.matchAll(/(?:width\s*(?:<=|>=|<|>)\s*([\d.]+)(px|em|rem))|(?:([\d.]+)(px|em|rem)\s*(?:<=|>=|<|>)\s*width)/g)) {
      const value = parseFloat(f[1] ?? f[3]);
      const unit = f[2] ?? f[4];
      if (unit !== "px" || !BREAKPOINTS.includes(value)) c.breakpoint++;
    }
  }

  for (const m of s.matchAll(/(?:^|[;{\s])(-{0,2}[a-z][a-z-]*)\s*:\s*([^;{}]+?)\s*(?=[;}])/g)) {
    const prop = m[1].toLowerCase();
    const value = m[2];
    if (prop.startsWith("--")) {
      /* A local custom property is a literal hiding behind a name; count its
         colours like any other value, its lengths not (it may be geometry). */
      c.colour += colours(value);
      continue;
    }
    if (COLOUR_PROPS.test(prop)) {
      const n = colours(value);
      c.colour += n;
      if (n && (prop === "box-shadow" || prop === "text-shadow" || (prop === "filter" && /drop-shadow/.test(value)))) c.shadow++;
    }
    if (/^(margin|padding)(-(top|right|bottom|left|inline|block)(-(start|end))?)?$|^(gap|row-gap|column-gap)$/.test(prop)) {
      c.spacing += lengths(value, { allowHairline: true, allowEm: false });
    }
    if (prop === "font-size") c.fontSize += lengths(value, { allowHairline: false, allowEm: true });
    if (/^border(-(top|bottom)-(left|right)|-(start|end)-(start|end))?-radius$/.test(prop)) {
      c.radius += lengths(value, { allowHairline: false, allowEm: true });
    }
  }
  return c;
}

function countJs(src) {
  const c = Object.fromEntries(CATEGORIES.map((k) => [k, 0]));
  const s = src.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/(^|[^:"'`])\/\/[^\n]*/g, "$1");
  for (const m of s.matchAll(/(["'`])((?:(?!\1)[^\\\n]|\\.)*)\1/g)) {
    c.colour += (m[2].match(HEX) || []).length + (m[2].match(FUNC) || []).length;
  }
  return c;
}

function countHtml(src) {
  const c = Object.fromEntries(CATEGORIES.map((k) => [k, 0]));
  for (const m of src.matchAll(/\b(?:style|fill|stroke)="([^"]*)"/g)) c.colour += colours(m[1]);
  return c;
}

/** { file: { category: n } } for every file with at least one literal. */
export function countAll(repo) {
  const out = {};
  for (const rel of sourceFiles(repo)) {
    const src = readFileSync(join(repo, rel), "utf8");
    const c = rel.endsWith(".js") ? countJs(src) : rel.endsWith(".html") ? countHtml(src) : countCss(src, rel.endsWith(".scss"));
    const nonzero = Object.fromEntries(Object.entries(c).filter(([, n]) => n > 0));
    if (Object.keys(nonzero).length) out[rel] = nonzero;
  }
  return out;
}
