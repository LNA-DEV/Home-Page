/* The download dialog — pick a size, read the licence, get a named file.

   docs/concepts/gallery-download-dialog.md is the design. Three things about
   this module are worth knowing before changing it:

   1. IT MAKES NO FILENAME. The `download` attribute's value is computed by
      Hugo (gallery-download-attrs.html) and arrives finished in
      data-download-name. The static card on the photo page carries the same
      string, so a sanitiser here would be a second implementation of the same
      five rules in a second language — and the path that has no JavaScript
      would be the one it did not cover.

   2. IT ONLY EVER ADDS THE GATE. The all-rights-reserved checkbox and the
      aria-disabled state are inserted by this script, never removed by it. The
      markup ships ungated, so with scripts off every link still works and the
      notice still sits above them. Ship it gated and "JS ungates on tick" and
      the gate becomes permanent for exactly the visitor it was never meant
      for.

   3. THE DEED IS PER LICENCE, NOT PER PHOTO. Each .gallery-item carries only
      data-license (25 bytes); the may/must/not lists come from params.licenses,
      resolved once per language in license-index.html. Emitting the deed per
      item would repeat ~400 bytes 572 times on the general grid.

   Everything is built with DOM nodes rather than an HTML string, so nothing
   here needs an escaper. */

import * as params from "@params";

const L = params.download || {};
const LICENSES = params.licenses || {};

/* Tier names by position from the top: the last row is always the original, the
   first is Small, whatever survives in between fills Medium and Large. The
   template applies the identical rule to the same list, which is what keeps the
   dialog and the static card labelling the same file the same way. */
const TIER_ORDER = ["small", "medium", "large"];

const sizeRequests = new Map();
const locale = document.documentElement.lang || "en";
const nf = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });

function formatBytes(n) {
  if (n >= 1e6) return `${nf.format(Math.round(n / 1e5) / 10)} MB`;
  if (n >= 1e3) return `${nf.format(Math.round(n / 1e3))} KB`;
  return `${nf.format(n)} B`;
}

/* One HEAD per tier when the dialog opens, memoised for the session. Hugo does
   not know these sizes — reading 1,296 renders per language is not a build cost
   worth paying, and the metadata pass rewrites every file after Hugo is done
   anyway, so a build-time number would be wrong as well as expensive. */
function fetchSize(url) {
  if (!sizeRequests.has(url)) {
    sizeRequests.set(
      url,
      fetch(url, { method: "HEAD" })
        .then((r) => {
          const len = r.ok ? Number(r.headers.get("content-length")) : NaN;
          return Number.isFinite(len) && len > 0 ? len : null;
        })
        .catch(() => null),
    );
  }
  return sizeRequests.get(url);
}

function parseLadder(packed) {
  if (!packed) return [];
  const rows = [];
  for (const part of packed.split("|")) {
    const sp = part.indexOf(" ");
    if (sp < 0) continue;
    const [w, h] = part.slice(0, sp).split("x").map(Number);
    const url = part.slice(sp + 1);
    if (!url || !Number.isFinite(w) || !Number.isFinite(h)) continue;
    rows.push({ w, h, url });
  }
  const last = rows.length - 1;
  return rows.map((r, i) => ({
    ...r,
    tier: i === last ? "original" : TIER_ORDER[i] || "large",
  }));
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

/* The credit line Creative Commons' own attribution guidance asks for: title,
   author, source, licence. A licence that requires permission gets none —
   there is nothing to attribute because there is nothing to reuse. */
function creditLine(title, artist, license, sourceUrl) {
  if (!license || license.requiresPermission) return "";
  const parts = [];
  if (title) parts.push(`"${title}"`);
  if (artist) parts.push(`${L.by || "by"} ${artist}`);
  const head = parts.join(" ");
  const name = license.short || license.label || "";
  return `${[head, name].filter(Boolean).join(", ")}\n${sourceUrl}`;
}

function copyButton(text) {
  const b = el("button", "photo-copy");
  b.type = "button";
  b.dataset.copy = text;
  b.dataset.labelCopy = L.copyCredit || "Copy";
  b.dataset.labelDone = L.copied || "Copied";
  b.title = b.dataset.labelCopy;
  b.setAttribute("aria-label", b.dataset.labelCopy);
  /* The same markup photo-meta.html emits: photo-page.js binds .photo-copy by
     delegation on document precisely so injected copies work, and CSS keeps it
     hidden until <html> has `has-clipboard`. Nothing to write for it here. */
  b.innerHTML =
    '<svg class="photo-copy__icon photo-copy__icon--copy" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>' +
    '<svg class="photo-copy__icon photo-copy__icon--done" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';
  return b;
}

let dialog = null;
let body = null;

function ensureDialog() {
  if (dialog) return dialog;
  dialog = el("dialog", "gallery-download");
  dialog.setAttribute("aria-label", L.heading || "Download");

  const head = el("div", "gallery-download__head");
  head.appendChild(el("h2", "gallery-download__heading", L.heading || "Download"));
  const close = el("button", "gallery-download__close", "×");
  close.type = "button";
  close.setAttribute("aria-label", L.close || "Close");
  close.addEventListener("click", () => dialog.close());
  head.appendChild(close);
  dialog.appendChild(head);

  body = el("div", "gallery-download__body");
  dialog.appendChild(body);

  /* A click on the backdrop lands on the dialog element itself, never on its
     children — the body fills it, so this is only ever the outside. */
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  document.body.appendChild(dialog);
  return dialog;
}

/* The gate, ADDED not removed: the size rows are built enabled and this turns
   them off until the box is ticked. It has no legal weight and is not meant to
   — its value is that the file cannot be taken before the sentence above it has
   been on screen. Creative Commons rows get none: their sentence grants rather
   than restricts, and reading it is a precondition of nothing. */
function addGate(container, rows, className) {
  const label = el("label", className);
  const box = document.createElement("input");
  box.type = "checkbox";
  label.appendChild(box);
  label.appendChild(el("span", null, L.gate || ""));
  container.appendChild(label);

  const apply = () => {
    for (const a of rows) a.setAttribute("aria-disabled", String(!box.checked));
  };
  box.addEventListener("change", apply);
  apply();

  for (const a of rows) {
    a.addEventListener("click", (e) => {
      if (a.getAttribute("aria-disabled") === "true") {
        e.preventDefault();
        box.focus();
      }
    });
  }
}

function buildSizeRow(t, name, imageId, licenseKey) {
  const a = el("a", "gallery-download__size");
  a.href = t.url;
  /* Computed by Hugo, read verbatim. */
  a.download = name;
  a.dataset.tier = t.tier;
  a.appendChild(el("span", "gallery-download__tier", L.tiers?.[t.tier] || t.tier));
  a.appendChild(el("span", "gallery-download__dims", `${t.w} × ${t.h}`));
  const size = el("span", "gallery-download__bytes", "");
  a.appendChild(size);
  a.appendChild(el("span", "gallery-download__hint", L.hints?.[t.tier] || ""));

  /* The row is usable the moment it renders; the byte size only ever fills in
     later, and a failed or slow HEAD simply leaves it blank. */
  fetchSize(t.url).then((bytes) => {
    if (bytes) size.textContent = formatBytes(bytes);
  });

  a.addEventListener("click", () => {
    /* A gated row reports nothing. The gate's own handler cancels the click,
       but it is registered AFTER this one (addGate runs once the rows exist),
       and listeners fire in registration order — so checking e.defaultPrevented
       here would always see false and every blocked click would be counted as a
       download. The attribute is the state itself and does not care who
       registered first. Without this the sixteen all-rights-reserved photos
       over-report by exactly the visitors who had to look for the checkbox,
       which is the comparison the event exists to make. */
    if (a.getAttribute("aria-disabled") === "true") return;
    window.plausible?.("Image Download", {
      props: { gallery_image_id: imageId || "", quality: t.tier, license: licenseKey || "" },
    });
  });
  return a;
}

export function openDownloadDialog(item) {
  if (!item) return;
  const d = ensureDialog();
  const caption = item.querySelector(".pswp-caption-content");
  const title = caption?.querySelector(".caption-title")?.textContent || item.title || "";
  const artist = caption?.querySelector(".caption-artist")?.textContent || "";
  const licenseKey = item.dataset.license || "";
  const license = LICENSES[licenseKey.toLowerCase()] || null;
  const tiers = parseLadder(item.dataset.downloads);
  const name = item.dataset.downloadName || "";
  /* data-page is the photo's own page. The hero on a photo page carries none,
     and there the page the visitor is on IS that page. */
  const source = item.dataset.page
    ? new URL(item.dataset.page, location.href).href
    : location.href.split("#")[0];

  body.textContent = "";
  if (title) body.appendChild(el("p", "gallery-download__title", title));

  if (license) {
    const sec = el("section", "gallery-download__license");
    const h = el("h3", null, L.licenseHeading || "License");
    sec.appendChild(h);
    if (license.url) {
      const a = el("a", "gallery-download__license-name", license.label || license.short || licenseKey);
      a.href = license.url;
      a.rel = "license noopener";
      sec.appendChild(a);
    } else {
      sec.appendChild(el("p", "gallery-download__license-name", license.label || licenseKey));
    }
    for (const kind of ["may", "must", "not"]) {
      const list = license.deed?.[kind] || [];
      if (!list.length) continue;
      const group = el("div", `gallery-download__deed gallery-download__deed--${kind}`);
      group.appendChild(el("h4", null, L[kind] || kind));
      const ul = el("ul");
      for (const line of list) ul.appendChild(el("li", null, line));
      group.appendChild(ul);
      sec.appendChild(group);
    }
    body.appendChild(sec);
  }

  const credit = creditLine(title, artist, license, source);
  if (credit) {
    const sec = el("section", "gallery-download__credit");
    sec.appendChild(el("h3", null, L.credit || "Credit line"));
    const row = el("div", "gallery-download__credit-row");
    row.appendChild(el("code", "gallery-download__credit-text", credit));
    row.appendChild(copyButton(credit));
    sec.appendChild(row);
    body.appendChild(sec);
  }

  /* The FLAG decides, never the key — a second restricted licence has to behave
     identically by carrying requires_permission, not by being named here. */
  if (license?.requiresPermission) {
    const sec = el("section", "gallery-download__notice");
    sec.appendChild(el("p", null, L.notice || ""));
    const links = el("p", "gallery-download__notice-links");
    if (params.authorEmail) {
      const a = el("a", null, L.contact || "");
      a.href = `mailto:${params.authorEmail}`;
      links.appendChild(a);
    }
    if (params.contactUrl) {
      if (links.childNodes.length) links.appendChild(el("span", null, " · "));
      const a = el("a", null, params.licensingLinkText || "");
      a.href = params.contactUrl;
      links.appendChild(a);
    }
    if (links.childNodes.length) sec.appendChild(links);
    body.appendChild(sec);
  }

  const sizes = el("section", "gallery-download__sizes");
  sizes.appendChild(el("h3", null, L.size || "Size"));
  const rows = tiers.map((t) => buildSizeRow(t, name, item.dataset.id, licenseKey));
  const list = el("div", "gallery-download__size-list");
  for (const a of rows) list.appendChild(a);
  sizes.appendChild(list);
  if (license?.requiresPermission) addGate(sizes, rows, "gallery-download__gate");
  body.appendChild(sizes);

  d.showModal();
}

export function isDownloadDialogOpen() {
  return Boolean(dialog?.open);
}

export function closeDownloadDialog() {
  if (dialog?.open) dialog.close();
}

/* THE STATIC CARD on the photo page. It renders complete and ungated; the only
   thing this adds is the gate, for the same reason the dialog has one. Nothing
   here is required for the card to work — that is the point of it. */
const card = document.querySelector(".photo-download[data-requires-permission]");
if (card) {
  const rows = Array.from(card.querySelectorAll(".photo-download__size"));
  const anchor = card.querySelector(".photo-download__sizes-heading");
  if (rows.length && anchor) {
    const holder = el("div", "photo-download__gate-holder");
    anchor.after(holder);
    /* The card's own class, not the dialog's: the two live in different
       stylesheets because they live on different backgrounds — the card inside
       the light/dark page (extended/gallery-download.css), the dialog only ever
       over the black lightbox (main.scss). Sharing one class here would have
       styled the card by whichever of the two happened to be loaded. */
    addGate(holder, rows, "photo-download__gate");
  }
}

/* Analytics for the static card's links, which never pass through the dialog. */
document.addEventListener("click", (e) => {
  const a = e.target.closest?.(".photo-download__size");
  if (!a) return;
  /* Same rule as the dialog rows above. Here the gate cannot stop the event
     reaching this listener at all: it calls preventDefault, not
     stopPropagation, so the click still bubbles to document. */
  if (a.getAttribute("aria-disabled") === "true") return;
  const item = document.querySelector(".gallery-item[data-license]");
  window.plausible?.("Image Download", {
    props: {
      gallery_image_id: item?.dataset.id || "",
      quality: a.dataset.tier || "",
      license: item?.dataset.license || "",
    },
  });
});
