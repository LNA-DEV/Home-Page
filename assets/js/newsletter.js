/* Newsletter subscribe form: a row of language pills and a row of topic
   bubbles, instead of the twelve raw checkboxes Listmonk's own generated form
   ships with.

   The lists are a language x topic matrix, so what gets submitted is the
   intersection of the two rows — pick 🇩🇪 + 🇬🇧 and "Photography" and two lists
   go out.

   Submission goes to the form action — Listmonk's /subscription/form — with
   fetch, so the visitor stays in the open panel: on success the form is
   replaced by the confirmation panel, on failure an inline error appears.

   Signing up needs JavaScript. The post carries the solution to Listmonk's
   ALTCHA proof of work (solveCaptcha() below), computed here in the background,
   so nobody sees a captcha. Without JavaScript nothing can solve it, and
   newsletter.css hides every placement rather than offering a form that can
   only fail.

   It is /subscription/form and NOT /api/public/subscription, which this file
   used to post to: Listmonk (v6.2.0) checks the captcha on the form endpoint
   only, and the API takes a signup without one. Posting to the API would make
   the captcha decorative — which is also why Caddy closes that route.

   Both messages are rendered server-side by the shortcode, so there is nothing
   to translate here — this file only toggles what is already on the page.

   The checkboxes inside .newsletter-raw stay the source of truth for which
   lists are selected; this file ticks them, hides them behind the pills, and
   reads them back when posting. */
(function () {
  for (const root of document.querySelectorAll(".newsletter")) init(root);
  initCta();

  /* Plausible. The queue stub is set up site-wide in extend_head.html, so the
     function exists even before the script has loaded — the guard is for the
     case where a blocker removed it. Never pass anything from the e-mail or
     name field: only which languages and topics were picked, which is exactly
     the aggregate worth knowing and carries nothing personal.

     `source` — "shortcode" | "header" | "post-footer" — rides along on every
     event. Several instances on one page are expected, so an event that does not
     say which one fired cannot answer the only question worth asking of this
     data: whether a placement earns its space. It lives out here rather than
     inside init() because the header's open event is raised from initCta(),
     which has no form instance to hang a closure on.

     NOT called send(): init() declares its own send() for posting the form, and
     a function declaration shadows the outer one inside it -- track() would then
     hand its arguments to the submitter and every successful signup would submit
     again on success, forever. */
  function trackEvent(source, name, props) {
    if (typeof window.plausible === "function")
      window.plausible(name, { props: { source: source || "unknown", ...props } });
  }

  /* The captcha: Listmonk's ALTCHA, a proof of work rather than a puzzle. The
     challenge names a hash and the salt it was made from; finding the number
     that, appended to the salt, gives that SHA-256 is the work — up to
     maxNumber tries (300,000 by default), around a second on a desktop and a
     cost per signup for a bot. The solution is the challenge sent back with the
     number, as base64 JSON, in the `altcha` field.

     Batches of 100 digests in parallel: one at a time is three times slower,
     larger batches gain nothing (measured in Node against altcha-lib-go, the
     library Listmonk verifies with).

     A 404 for the challenge means ALTCHA is off in Listmonk. The form then
     posts without a solution, which Listmonk accepts in exactly that state —
     what lets the site deploy before the captcha is switched on, and keeps the
     form working if it is ever switched off again. */
  async function fetchCaptcha(url) {
    const res = await fetch(url);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`captcha challenge: HTTP ${res.status}`);
    return solveCaptcha(await res.json());
  }

  async function solveCaptcha(task) {
    if (task.algorithm !== "SHA-256") throw new Error(`captcha: ${task.algorithm}`);
    const want = Uint8Array.from(task.challenge.match(/../g), (h) => parseInt(h, 16));
    const matches = (buf) => {
      const got = new Uint8Array(buf);
      return want.every((b, i) => got[i] === b);
    };
    const utf8 = new TextEncoder();
    for (let start = 0; start <= task.maxNumber; start += 100) {
      const end = Math.min(start + 100, task.maxNumber + 1);
      const tries = [];
      for (let n = start; n < end; n++)
        tries.push(crypto.subtle.digest("SHA-256", utf8.encode(task.salt + n)));
      const hit = (await Promise.all(tries)).findIndex(matches);
      if (hit !== -1)
        return btoa(JSON.stringify({
          algorithm: task.algorithm,
          challenge: task.challenge,
          number: start + hit,
          salt: task.salt,
          signature: task.signature,
        }));
    }
    throw new Error("captcha: no solution");
  }

  /* The header CTA. A link to Listmonk's own subscription page, so a middle
     click or "open in new tab" lands on a page that works by itself, with its
     own ALTCHA widget. Here we take the plain click back and open the dialog
     instead.

     showModal(), not the open attribute: only the modal form puts the dialog in
     the top layer and brings the focus trap, the ESC handler and ::backdrop with
     it. Everything below is the one thing it does NOT give us — dismissing on a
     click outside. The check works because the backdrop is painted by the dialog
     element itself, so a click on it reports the dialog as its target, while a
     click on any real content reports a descendant. */
  function initCta() {
    const link = document.querySelector("[data-newsletter-open]");
    const modal = document.querySelector(".newsletter-modal");
    if (!link || !modal || typeof modal.showModal !== "function") return;

    /* This click IS the open event for this placement: there is no panel to
       unfold, the dialog is the panel. It is the one placement where the click
       is the whole point, so leaving it unrecorded meant the header reported
       signups against no denominator at all.

       Counted once per page view, exactly like the <details> toggle below —
       someone who opens the dialog, dismisses it and opens it again is one
       interested visitor, not two.

       The source is read back off the form inside the dialog instead of being
       written out here, so this cannot drift from what newsletter-cta.html
       actually passed to the partial. */
    const instance = modal.querySelector(".newsletter");
    const source = instance && instance.dataset.source;
    let openTracked = false;

    link.addEventListener("click", (event) => {
      event.preventDefault();
      modal.showModal();
      if (openTracked) return;
      openTracked = true;
      trackEvent(source, "Newsletter Open");
    });

    modal.addEventListener("click", (event) => {
      if (event.target === modal) modal.close();
    });
  }

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

    // Which placement this instance is: "shortcode" | "header" | "post-footer",
    // set by newsletter-form.html. See trackEvent() for why every event carries it.
    const source = root.dataset.source;
    const track = (name, props) => trackEvent(source, name, props);

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
    // Two of the three placements raise this event: the shortcode here, and the
    // header from its CTA click in initCta(). The post-footer block cannot —
    // it renders already open, so there is no opening to record and no listener
    // to attach, since "toggle" on a <div> would never fire. That is worth
    // knowing when reading the stats: that placement reports signups but no
    // opens, so it is comparable to the others on conversions, not on funnel
    // top. Giving it an equivalent would mean an IntersectionObserver ("was it
    // ever scrolled into view"), which answers a different question and is
    // deliberately not built.
    if (root.tagName === "DETAILS") {
      let openTracked = false;
      root.addEventListener("toggle", () => {
        if (!root.open || openTracked) return;
        openTracked = true;
        track("Newsletter Open");   // props: just the source, added by track()
      });
    }

    // Solved ahead, from the moment the visitor starts on the form, so the work
    // is done while they type rather than after they click. The challenge
    // expires after five minutes and a solution is good for one post, so one
    // older than four minutes is replaced, and send() takes it and drops it.
    const captchaUrl = form.dataset.captcha;
    let captcha = null;   // { at, promise }
    function prepareCaptcha() {
      if (!captchaUrl) return Promise.resolve(null);
      if (!captcha || Date.now() - captcha.at > 4 * 60 * 1000) {
        captcha = { at: Date.now(), promise: fetchCaptcha(captchaUrl) };
        // Reported when send() awaits it, not as an unhandled rejection now.
        captcha.promise.catch(() => {});
      }
      return captcha.promise;
    }
    form.addEventListener("focusin", prepareCaptcha);

    form.addEventListener("submit", (event) => {
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
        // Usually solved on focus already; awaited here in case the visitor was
        // quicker, and started here if the form never had focus (a password
        // manager filling it, say).
        const pending = prepareCaptcha();
        captcha = null;
        const solution = await pending;

        // Form-encoded, and it has to be: the form endpoint reads the captcha
        // and the honeypot as form fields, so a JSON body would lose them. It
        // is also what keeps this a "simple" CORS request, so the browser
        // sends no OPTIONS preflight and Listmonk only has to add one response
        // header (it does, for every origin under Settings -> Security ->
        // Trusted URLs). URLSearchParams sets the content type itself —
        // setting it by hand here would break the simple request.
        const body = new URLSearchParams();
        body.set("email", email.value);
        if (name) body.set("name", name.value);
        for (const uuid of lists) body.append("l", uuid);
        if (solution) body.set("altcha", solution);

        const res = await fetch(form.action, { method: "POST", body });
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
        // Listmonk answers with an HTML page in Listmonk's language, not the
        // visitor's, so only the status goes to the console and the visitor
        // gets the translated message. 400 is also a rejected captcha.
        console.warn("newsletter:", res.status, res.statusText);
        track("Newsletter Error", { reason: String(res.status) });
        showError(true);
      } catch (err) {
        // Never reached Listmonk at all (missing CORS header, offline, blocked),
        // or the captcha could not be fetched or solved.
        // Deliberately NOT falling back to form.submit() here. That would post
        // the old way and dump the visitor on a Listmonk page, which is
        // indistinguishable from the newsletter simply not working and hides the
        // actual cause. A visible error beats a silent redirect.
        console.warn("newsletter: request failed (CORS?)", err);
        // fetchCaptcha() and solveCaptcha() prefix their own errors.
        const reason = /^captcha/.test(err && err.message) ? "captcha" : "network";
        track("Newsletter Error", { reason });
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
