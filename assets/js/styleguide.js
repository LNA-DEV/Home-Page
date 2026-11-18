/* The styleguide's colour swatches (layouts/partials/styleguide.html).

   Lists every custom property declared on :root in the site's stylesheets —
   which is assets/css/core/theme-vars.css — whose value is a colour, and draws
   one swatch per token in each theme panel. Reading the CSSOM instead of a
   hand-kept list means the page cannot fall behind the tokens file. */

function tokenNames() {
  const names = new Set();
  for (const sheet of document.styleSheets) {
    let rules;
    try {
      rules = sheet.cssRules;
    } catch {
      continue; // a cross-origin sheet; the site has none, but be safe
    }
    for (const rule of rules) {
      if (rule.selectorText !== ":root" || !rule.style) continue;
      for (const prop of rule.style) {
        if (prop.startsWith("--")) names.add(prop);
      }
    }
  }
  return [...names];
}

function isColour(value) {
  return value !== "" && CSS.supports("color", value) && !/^var\(/.test(value);
}

function draw(panel, names) {
  const root = getComputedStyle(document.documentElement);
  const probe = document.createElement("span");
  panel.appendChild(probe);
  const out = panel.querySelector("[data-swatches]");
  for (const name of names) {
    const raw = root.getPropertyValue(name).trim();
    if (!isColour(raw)) continue;
    probe.style.color = `var(${name})`;
    const resolved = getComputedStyle(probe).color;
    const item = document.createElement("div");
    item.className = "sg-swatch";
    const swatch = document.createElement("i");
    swatch.style.background = `var(${name})`;
    const label = document.createElement("code");
    label.textContent = name;
    const value = document.createElement("span");
    value.textContent = resolved;
    item.append(swatch, label, value);
    out.appendChild(item);
  }
  probe.remove();
}

const names = tokenNames();
document.querySelectorAll(".sg-theme").forEach((panel) => draw(panel, names));
