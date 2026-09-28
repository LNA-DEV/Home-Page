/* The screenshot strip on a game page (layouts/partials/game-detail.html).

   Plain PhotoSwipe on the vendored module, and deliberately not lightbox.js:
   that one is built around the gallery — likes, deep links to a photo's UUID,
   EXIF captions, the download dialog — none of which a screenshot has. Each
   thumbnail is an ordinary link to the large variant, so without JavaScript it
   still opens the image. Loaded only on pages that have screenshots (head.html). */

import PhotoSwipeLightbox from "./photoswipe/photoswipe-lightbox.esm.js";
import PhotoSwipe from "./photoswipe/photoswipe.esm.js";
import * as params from "@params";

const strip = document.querySelector("[data-game-shots]");
if (strip) {
  const lightbox = new PhotoSwipeLightbox({
    gallery: strip,
    children: "a.game-shot",
    pswpModule: PhotoSwipe,
    closeTitle: params.closeTitle,
    zoomTitle: params.zoomTitle,
    arrowPrevTitle: params.arrowPrevTitle,
    arrowNextTitle: params.arrowNextTitle,
    errorMsg: params.errorMsg,
  });
  lightbox.init();
}
