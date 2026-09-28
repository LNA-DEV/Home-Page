/* Achievement lists on a game page (layouts/partials/game-achievements.html):
   filter all / unlocked / locked, sort default / rarest first / A–Z.

   The server renders the default order already, and the controls `hidden`, so
   without JavaScript the list is complete and correctly ordered and there are
   no buttons that do nothing. Each block works on its own — a game with lists
   on two stores gets two independent sets of controls. */

function pct(row) {
  const v = parseFloat(row.dataset.pct);
  return v >= 0 ? v : Infinity; // no percentage: after every known one
}

function order(row) {
  return parseInt(row.dataset.order, 10) || 0;
}

const COMPARE = {
  default: (a, b) => order(a) - order(b),
  rarity: (a, b) => pct(a) - pct(b) || order(a) - order(b),
  alpha: (a, b) => a.dataset.name.localeCompare(b.dataset.name) || order(a) - order(b),
};

document.querySelectorAll("[data-achievements]").forEach((block) => {
  const list = block.querySelector(".game-achv-list");
  const controls = block.querySelector(".game-achv-controls");
  if (!list || !controls) return;
  const rows = Array.from(list.children);
  let filter = "all";
  let sort = "default";

  function apply() {
    rows
      .slice()
      .sort(COMPARE[sort] || COMPARE.default)
      .forEach((row) => {
        row.hidden = filter !== "all" && row.dataset.state !== filter;
        list.appendChild(row);
      });
  }

  function wire(attr, set) {
    const buttons = controls.querySelectorAll(`[${attr}]`);
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        buttons.forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        set(btn.getAttribute(attr));
        apply();
      });
    });
  }

  wire("data-achv-filter", (v) => { filter = v; });
  wire("data-achv-sort", (v) => { sort = v; });
  controls.hidden = false;
});
