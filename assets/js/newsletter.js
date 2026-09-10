/* Newsletter subscribe form: a row of language pills and a row of topic
   bubbles, instead of the twelve raw checkboxes Listmonk's own generated form
   ships with.

   The lists are a language x topic matrix, so what gets submitted is the
   intersection of the two rows — pick 🇩🇪 + 🇬🇧 and "Photography" and two lists
   go out.

   Submission goes to Listmonk's public API (data/newsletter.yaml -> api, passed
   down as data-api) rather than to the form action, so the visitor stays in the
   open panel: on success the form is replaced by the confirmation panel, on
   failure an inline error appears. Only JavaScript being off falls back to the
   plain cross-site POST; a failed request reports itself rather than quietly
   navigating away.

   Both messages are rendered server-side by the shortcode, so there is nothing
   to translate here — this file only toggles what is already on the page.

   The checkboxes inside .newsletter-raw stay the source of truth for which
   lists are selected; this file ticks them, hides them behind the pills, and
   reads them back when posting. */
(function () {
  for (const root of document.querySelectorAll(".newsletter")) init(root);

  function init(root) {
    const form = root.querySelector(".newsletter-form");
    const picker = root.querySelector(".newsletter-picker");
    const raw = root.querySelector(".newsletter-raw");
    const submit = root.querySelector(".newsletter-submit");
    const error = root.querySelector(".newsletter-status");
    const done = root.querySelector(".newsletter-done");
    if (!form || !picker || !raw || !submit) return;

    const boxes = Array.from(raw.querySelectorAll('input[type="checkbox"]'));
    const langPills = Array.from(picker.querySelectorAll("[data-lang]"));
    const topicPills = Array.from(picker.querySelectorAll("[data-topic]"));

    const setPressed = (pill, on) => {
      pill.classList.toggle("active", on);
      pill.setAttribute("aria-pressed", on ? "true" : "false");
    };
    const isPressed = (pill) => pill.classList.contains("active");
    const selected = (pills, key) =>
      pills.filter(isPressed).map((pill) => pill.dataset[key]);
    const checkedLists = () =>
      boxes.filter((box) => box.checked).map((box) => box.value);
    const showError = (on) => {
      if (error) error.hidden = !on;
    };

    /* Plausible. The queue stub is set up site-wide in extend_head.html, so the
       function exists even before the script has loaded — the guard is for the
       case where a blocker removed it. Never pass anything from the e-mail or
       name field: only which languages and topics were picked, which is exactly
       the aggregate worth knowing and carries nothing personal. */
    // Which placement this instance is: "shortcode" | "header" | "post-footer".
    // Set by newsletter-form.html. It rides along on every event because two
    // instances on one page are expected, and an event that does not say which
    // one fired cannot answer the only question worth asking of this data --
    // whether a placement earns its space.
    const source = root.dataset.source || "unknown";

    const track = (name, props) => {
      if (typeof window.plausible === "function")
        window.plausible(name, { props: { source, ...props } });
    };

    function sync() {
      const langs = selected(langPills, "lang");
      const topics = selected(topicPills, "topic");
      for (const box of boxes) {
        box.checked =
          langs.includes(box.dataset.lang) && topics.includes(box.dataset.topic);
      }
      // Listmonk rejects a submission that carries no list at all.
      submit.disabled = checkedLists().length === 0;
    }

    // English always, plus the language of the page being read, plus whatever the
    // browser asks for.
    //
    // The page language comes from the shortcode as data-page-lang rather than
    // being parsed out of the URL: the site puts every language in its own path
    // segment, but that is a config decision (defaultContentLanguageInSubdir),
    // not something this file should encode.
    //
    // It matters because the browser's languages and the page's are routinely
    // different -- someone on an English-language system reading the German post
    // used to end up subscribed to the English list only, which is the opposite
    // of what picking the German article signals. Only navigator.languages is
    // genuinely unknowable to a static build; the page language is not, and was
    // simply missing here.
    const wanted = new Set(["en"]);
    if (root.dataset.pageLang) wanted.add(root.dataset.pageLang);
    for (const tag of navigator.languages || [navigator.language || ""]) {
      wanted.add(String(tag).toLowerCase().split("-")[0]);
    }
    for (const pill of langPills) setPressed(pill, wanted.has(pill.dataset.lang));
    for (const pill of topicPills) setPressed(pill, true);

    picker.addEventListener("click", (event) => {
      const pill = event.target.closest(".newsletter-pill");
      if (!pill) return;
      setPressed(pill, !isPressed(pill));
      showError(false);
      sync();
    });

    // Opening the panel is the top of the funnel: it says how many people were
    // interested at all, which the signup count alone cannot. Once per page
    // view — a visitor folding it open and shut would otherwise inflate it.
    //
    // Only the <details> variant has this event. The post-footer block renders
    // already open, so there is no opening to record and no listener to attach —
    // "toggle" on a <div> would simply never fire. The consequence is worth
    // knowing when reading the stats: that placement reports signups but no
    // opens, so the two placements are comparable on conversions, not on funnel
    // top. Recording an equivalent for it would mean an IntersectionObserver
    // ("was it ever scrolled into view"), which is a different question and not
    // one anybody has asked yet.
    if (root.tagName === "DETAILS") {
      let openTracked = false;
      root.addEventListener("toggle", () => {
        if (!root.open || openTracked) return;
        openTracked = true;
        track("Newsletter Open");   // props: just the source, added by track()
      });
    }

    const api = form.dataset.api;
    if (api) form.addEventListener("submit", (event) => {
      event.preventDefault();
      send();
    });

    async function send() {
      const honeypot = form.querySelector('input[name="nonce"]');
      if (honeypot && honeypot.value) return; // a bot filled it in

      const email = form.querySelector('input[name="email"]');
      const name = form.querySelector('input[name="name"]');
      const lists = checkedLists();
      if (!lists.length) return;

      // Sorted, so "de,en" and "en,de" are one value in Plausible rather than two.
      const picked = {
        languages: selected(langPills, "lang").sort().join(","),
        topics: selected(topicPills, "topic").sort().join(","),
      };

      showError(false);
      submit.disabled = true;
      try {
        // Form-encoded, not JSON, and deliberately so: a urlencoded body is a
        // "simple" CORS request, so the browser sends no OPTIONS preflight and
        // the reverse proxy in front of Listmonk only has to add one response
        // header. A JSON body would need the proxy to answer preflights too.
        // Listmonk's public endpoint takes both; the form variant repeats `l`
        // where the JSON one takes list_uuids. URLSearchParams sets the content
        // type itself — setting it by hand here would break the simple request.
        const body = new URLSearchParams();
        body.set("email", email.value);
        if (name) body.set("name", name.value);
        for (const uuid of lists) body.append("l", uuid);

        const res = await fetch(api, { method: "POST", body });
        if (res.ok) {
          track("Newsletter Signup", picked);
          // Hand the whole panel over to the confirmation — but only if there is
          // one to hand it to. Hiding the form without it leaves an empty box,
          // which is what a stale page (script rebuilt, HTML not) looks like.
          if (done) {
            form.hidden = true;
            done.hidden = false;
          } else {
            console.warn("newsletter: .newsletter-done missing, keeping the form");
          }
          return;
        }
        // Listmonk's own message is in Listmonk's language, not the visitor's,
        // so it goes to the console and the visitor gets the translated one.
        const answer = await res.json().catch(() => ({}));
        console.warn("newsletter:", res.status, answer.message || res.statusText);
        track("Newsletter Error", { reason: String(res.status) });
        showError(true);
      } catch (err) {
        // Never reached Listmonk at all: missing CORS header, offline, blocked.
        // Deliberately NOT falling back to form.submit() here. That would post
        // the old way and dump the visitor on a Listmonk page, which is
        // indistinguishable from the newsletter simply not working and hides the
        // actual cause. A visible error beats a silent redirect.
        console.warn("newsletter: request failed (CORS?)", err);
        track("Newsletter Error", { reason: "network" });
        showError(true);
      } finally {
        sync();
      }
    }

    sync();
    raw.hidden = true;
    picker.hidden = false;
  }
})();
