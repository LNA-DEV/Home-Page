/* Newsletter subscribe form: a row of language pills and a row of topic
   bubbles, instead of the ten raw checkboxes Listmonk's own generated form
   ships with.

   The nine blog lists are a language x topic matrix, so what gets submitted is
   the intersection of the two rows — pick 🇩🇪 + 🇬🇧 and "Photography" and two
   lists are ticked. Lists that are not part of that matrix (new photos) carry
   data-list instead of data-lang/data-topic and are toggled on their own.

   The checkboxes inside .newsletter-raw are what is actually posted; this file
   only ticks them and hides them behind the pills. With JavaScript off that
   plain list stays visible and the form still works — which is what the Tor
   build falls back to. */
(function () {
  for (const root of document.querySelectorAll(".newsletter")) init(root);

  function init(root) {
    const picker = root.querySelector(".newsletter-picker");
    const raw = root.querySelector(".newsletter-raw");
    const submit = root.querySelector(".newsletter-submit");
    if (!picker || !raw || !submit) return;

    const boxes = Array.from(raw.querySelectorAll('input[type="checkbox"]'));
    const langPills = Array.from(picker.querySelectorAll("[data-lang]"));
    const topicPills = Array.from(picker.querySelectorAll("[data-topic]"));
    const listPills = Array.from(picker.querySelectorAll("[data-list]"));

    const setPressed = (pill, on) => {
      pill.classList.toggle("active", on);
      pill.setAttribute("aria-pressed", on ? "true" : "false");
    };
    const isPressed = (pill) => pill.classList.contains("active");
    const selected = (pills, key) =>
      pills.filter(isPressed).map((pill) => pill.dataset[key]);

    function sync() {
      const langs = selected(langPills, "lang");
      const topics = selected(topicPills, "topic");
      const lists = selected(listPills, "list");

      let any = false;
      for (const box of boxes) {
        const on = box.dataset.list
          ? lists.includes(box.dataset.list)
          : langs.includes(box.dataset.lang) &&
            topics.includes(box.dataset.topic);
        box.checked = on;
        any = any || on;
      }

      // Listmonk rejects a submission that carries no list at all.
      submit.disabled = !any;
    }

    // English always, plus whatever the browser asks for. This is the one thing
    // a static build cannot know, and the reason any of this runs client-side.
    const wanted = new Set(["en"]);
    for (const tag of navigator.languages || [navigator.language || ""]) {
      wanted.add(String(tag).toLowerCase().split("-")[0]);
    }
    for (const pill of langPills) setPressed(pill, wanted.has(pill.dataset.lang));
    for (const pill of topicPills) setPressed(pill, true);
    for (const pill of listPills) setPressed(pill, true);

    picker.addEventListener("click", (event) => {
      const pill = event.target.closest(".newsletter-pill");
      if (!pill) return;
      setPressed(pill, !isPressed(pill));
      sync();
    });

    sync();
    raw.hidden = true;
    picker.hidden = false;
  }
})();
