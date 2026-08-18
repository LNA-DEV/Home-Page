/* Photo dex overview: group pills, text search, and a "photographed only"
   toggle. Every species card is already in the DOM, so this only ever hides
   and shows — no fetching, no re-rendering, and the page still works with
   JavaScript off (you just see all of them). */
(function () {
  const root = document.querySelector("[data-dex]");
  if (!root) return;

  const grid = root.querySelector("[data-dex-grid]");
  const cards = Array.from(root.querySelectorAll(".dex-card"));
  const pills = Array.from(root.querySelectorAll(".dex-pill"));
  const search = root.querySelector("[data-dex-search]");
  const onlyCaught = root.querySelector("[data-dex-only-caught]");
  const empty = root.querySelector("[data-dex-empty]");
  if (!grid || !cards.length) return;

  const state = { group: "all", query: "", caughtOnly: false };

  function apply() {
    let visible = 0;
    for (const card of cards) {
      const matchesGroup =
        state.group === "all" || card.dataset.group === state.group;
      const matchesQuery =
        !state.query || (card.dataset.search || "").includes(state.query);
      const matchesCaught = !state.caughtOnly || card.dataset.caught === "1";
      const show = matchesGroup && matchesQuery && matchesCaught;
      card.hidden = !show;
      if (show) visible += 1;
    }
    if (empty) empty.hidden = visible !== 0;
  }

  for (const pill of pills) {
    pill.addEventListener("click", () => {
      for (const other of pills) other.classList.toggle("is-active", other === pill);
      state.group = pill.dataset.group || "all";
      apply();
    });
  }

  if (search) {
    search.addEventListener("input", () => {
      state.query = search.value.trim().toLowerCase();
      apply();
    });
  }

  if (onlyCaught) {
    onlyCaught.addEventListener("change", () => {
      state.caughtOnly = onlyCaught.checked;
      apply();
    });
  }

  apply();
})();
