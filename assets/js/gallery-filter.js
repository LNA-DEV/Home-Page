// Client-side gallery filtering via data-category attributes.

(function () {
  var filters = document.querySelector(".gallery-filters");
  if (!filters) return;

  var pills = filters.querySelectorAll(".filter-pill");
  var gallery = document.getElementById("gallery");
  if (!gallery) return;

  var items = gallery.querySelectorAll(".gallery-item");
  if (items.length === 0) return;

  pills.forEach(function (pill) {
    pill.addEventListener("click", function () {
      var category = pill.getAttribute("data-category");
      var showAll = category === "all";

      items.forEach(function (item) {
        if (showAll || item.getAttribute("data-category") === category) {
          item.style.display = "";
        } else {
          item.style.display = "none";
        }
      });

      pills.forEach(function (p) {
        p.classList.remove("active");
      });
      pill.classList.add("active");
    });
  });
})();
