/* Per-photo page enhancements.

   Copy-to-clipboard for the permalink, bound by delegation rather than to the
   buttons directly: the same markup is injected into the lightbox popup from
   the fetched info fragment, so a one-shot querySelectorAll at load would miss
   every copy of it.

   Visibility is a CSS concern, not a JS one, for the same reason — the button
   is display:none until `has-clipboard` lands on <html>, which covers injected
   copies automatically and means a visitor without JS or without the Clipboard
   API never sees a control that would do nothing. */
if (navigator.clipboard) {
  document.documentElement.classList.add("has-clipboard");
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest(".photo-copy[data-copy]");
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();

  try {
    await navigator.clipboard.writeText(button.dataset.copy);
  } catch {
    return; // permission denied or insecure context — leave the control silent
  }

  const done = button.dataset.labelDone || "Copied";
  const idle = button.dataset.labelCopy || "Copy link";
  button.classList.add("is-copied");
  button.setAttribute("title", done);
  button.setAttribute("aria-label", done);
  clearTimeout(button._copyTimer);
  button._copyTimer = setTimeout(() => {
    button.classList.remove("is-copied");
    button.setAttribute("title", idle);
    button.setAttribute("aria-label", idle);
  }, 1600);
});
