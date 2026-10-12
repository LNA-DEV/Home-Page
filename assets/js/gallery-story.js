/* Story / Grid on a gallery project with project_layout essay or journal
   (docs/concepts/gallery-project-stories.md §5.4).

   The page renders both: the story, then the grid (#grid). Without JavaScript
   that is what a visitor gets, and the toggle stays `hidden`. With it, one of
   the two shows at a time, and the state lives in the URL hash:

     #grid          the grid
     #<uuid>        the grid too — lightbox.js opens that photo from the hash,
                    and it needs the grid visible to find it
     anything else  the story (a chapter anchor, #map, an outing)

   Closing a lightbox that was opened from a deep link goes back to the bare
   page URL. That must not throw the visitor into the story, so an empty hash
   right after a photo's hash keeps the view it had. */

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function init() {
  const page = document.querySelector(".story-page");
  if (!page) return;
  const toggle = page.querySelector(".story-toggle");
  const buttons = toggle ? Array.from(toggle.querySelectorAll("button[data-view]")) : [];

  const hashNow = () => decodeURIComponent(window.location.hash.slice(1));
  let lastHash = hashNow();

  function viewFor(hash, previousHash) {
    if (hash === "grid" || UUID.test(hash)) return "grid";
    if (hash === "" && UUID.test(previousHash)) return page.dataset.view || "grid";
    return "story";
  }

  function apply(view) {
    page.dataset.view = view;
    for (const b of buttons) b.setAttribute("aria-pressed", String(b.dataset.view === view));
  }

  /* Bring the top of the page into view after a switch made further down —
     the "Show as grid" link at the end of the story. */
  function toTop() {
    const top = page.getBoundingClientRect().top + window.scrollY;
    if (window.scrollY > top) window.scrollTo({ top: Math.max(0, top - 16) });
  }

  function onNavigate() {
    const hash = hashNow();
    if (hash === lastHash) return;
    const before = page.dataset.view;
    const view = viewFor(hash, lastHash);
    lastHash = hash;
    if (view === before) return;
    apply(view);
    if (view === "grid" && hash === "grid") toTop();
  }

  function switchTo(view) {
    if (view === page.dataset.view) return;
    const url = window.location.pathname + window.location.search + (view === "grid" ? "#grid" : "");
    history.pushState(null, "", url);
    lastHash = view === "grid" ? "grid" : "";
    apply(view);
  }

  if (toggle) toggle.hidden = false;
  apply(viewFor(lastHash, ""));

  for (const b of buttons) b.addEventListener("click", () => switchTo(b.dataset.view));

  /* "Show as grid" at the end of the story is a plain #grid link, so it works
     without JavaScript. With it, footer.html's smooth scrolling would take the
     click first — preventDefault and pushState, which fires no hashchange — and
     scroll towards a grid that is still hidden. Caught in the capture phase,
     before that handler on the link itself. */
  document.addEventListener(
    "click",
    (e) => {
      const link = e.target instanceof Element ? e.target.closest('a[href="#grid"]') : null;
      if (!link || !page.contains(link)) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      switchTo("grid");
      toTop();
    },
    true,
  );

  window.addEventListener("hashchange", onNavigate);
  window.addEventListener("popstate", onNavigate);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
else init();
