import PhotoSwipeLightbox from "./photoswipe/photoswipe-lightbox.esm.js";
import PhotoSwipe from "./photoswipe/photoswipe.esm.js";
import PhotoSwipeDynamicCaption from "./photoswipe/photoswipe-dynamic-caption-plugin.esm.min.js";
import * as params from "@params";

const gallery = document.getElementById("gallery");
const companionUrl = params.companionUrl || "";

// Cache for like data to avoid duplicate API calls
const likeDataCache = new Map();
// Cache for native like status
const nativeLikeStatusCache = new Map();

// Platform display names
const platformNames = {
  bluesky: "Bluesky",
  instagram: "Instagram",
  pixelfed: "Pixelfed",
  native: "This site",
};

// Get or create user token for native likes
function getUserToken() {
  const storageKey = "gallery-like-token";
  let token = localStorage.getItem(storageKey);
  if (!token) {
    token = crypto.randomUUID();
    localStorage.setItem(storageKey, token);
  }
  return token;
}

// Check if user has liked an image
async function getNativeLikeStatus(imageName) {
  if (nativeLikeStatusCache.has(imageName)) {
    return nativeLikeStatusCache.get(imageName);
  }

  try {
    const token = getUserToken();
    const response = await fetch(
      `${companionUrl}/api/interactions/native/${encodeURIComponent(imageName)}/status?token=${encodeURIComponent(token)}`
    );
    if (!response.ok) return false;

    const data = await response.json();
    const liked = data.has_liked || false;
    nativeLikeStatusCache.set(imageName, liked);
    return liked;
  } catch (error) {
    return false;
  }
}

// Toggle native like for an image
async function toggleNativeLike(imageName) {
  const token = getUserToken();
  const currentlyLiked = nativeLikeStatusCache.get(imageName) || false;

  try {
    const response = await fetch(
      `${companionUrl}/api/interactions/native/${encodeURIComponent(imageName)}/like`,
      {
        method: currentlyLiked ? "DELETE" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      }
    );

    if (response.ok) {
      const newStatus = !currentlyLiked;
      nativeLikeStatusCache.set(imageName, newStatus);
      // Invalidate like data cache to force refresh
      likeDataCache.delete(imageName);
      return newStatus;
    }
    return currentlyLiked;
  } catch (error) {
    return currentlyLiked;
  }
}

// Fetch like data for a single image
async function fetchLikeData(imageName) {
  if (likeDataCache.has(imageName)) {
    return likeDataCache.get(imageName);
  }

  try {
    const response = await fetch(`${companionUrl}/api/interactions/post/all/${encodeURIComponent(imageName)}`);
    if (!response.ok) return { platforms: [], total: 0 };

    const data = await response.json();
    const platforms = data.filter((p) => p.likes > 0);
    const total = data.reduce((sum, platform) => sum + (platform.likes || 0), 0);
    const result = { platforms, total };
    likeDataCache.set(imageName, result);
    return result;
  } catch (error) {
    return { platforms: [], total: 0 };
  }
}

// Generate tooltip HTML for platform breakdown
function generateTooltipHtml(platforms) {
  if (platforms.length === 0) return "";
  return `<div class="like-tooltip">${platforms
    .map((p) => `<div class="like-tooltip-row"><span>${platformNames[p.platform] || p.platform}</span><span>${p.likes}</span></div>`)
    .join("")}</div>`;
}

// Heart SVG icons
const heartOutline = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`;
const heartFilled = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>`;
const heartFilledLarge = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>`;
const heartOutlineLarge = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`;

// Render like count element
function renderLikeCount(el, total, platforms, liked, large = false) {
  const icon = liked ? (large ? heartFilledLarge : heartFilled) : (large ? heartOutlineLarge : heartOutline);
  el.innerHTML = `${icon}${total}${generateTooltipHtml(platforms)}`;
  el.classList.toggle("liked", liked);
}

// Fetch and display like counts for gallery images
async function fetchLikeCounts() {
  const galleryItems = document.querySelectorAll(".gallery-item[data-image-name]");

  for (const item of galleryItems) {
    const imageName = item.dataset.imageName;
    const likeCountEl = item.querySelector(".like-count");

    if (!imageName || !likeCountEl) continue;

    const [{ platforms, total }, liked] = await Promise.all([
      fetchLikeData(imageName),
      getNativeLikeStatus(imageName),
    ]);

    // Always show the like button (even with 0 likes) so users can like
    renderLikeCount(likeCountEl, total, platforms, liked);
    likeCountEl.classList.add("visible");

    // Add click handler for native like toggle
    likeCountEl.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const newLiked = await toggleNativeLike(imageName);
      const { platforms: newPlatforms, total: newTotal } = await fetchLikeData(imageName);
      renderLikeCount(likeCountEl, newTotal, newPlatforms, newLiked);
    });
  }
}

if (gallery) {
  fetchLikeCounts();
}

if (gallery) {
  const lightbox = new PhotoSwipeLightbox({
    gallery,
    children: ".gallery-item",
    showHideAnimationType: "zoom",
    bgOpacity: 1,
    pswpModule: PhotoSwipe,
    imageClickAction: "close",
    paddingFn: (viewportSize) => {
      return viewportSize.x < 700
        ? {
            top: 0,
            bottom: 0,
            left: 0,
            right: 0,
          }
        : {
            top: 30,
            bottom: 30,
            left: 0,
            right: 0,
          };
    },
    closeTitle: params.closeTitle,
    zoomTitle: params.zoomTitle,
    arrowPrevTitle: params.arrowPrevTitle,
    arrowNextTitle: params.arrowNextTitle,
    errorMsg: params.errorMsg,
  });

  lightbox.on("uiRegister", () => {
    lightbox.pswp.ui.registerElement({
      name: "download-button",
      order: 8,
      isButton: true,
      tagName: "a",
      html: {
        isCustomSVG: true,
        inner: '<path d="M20.5 14.3 17.1 18V10h-2.2v7.9l-3.4-3.6L10 16l6 6.1 6-6.1ZM23 23H9v2h14Z" id="pswp__icn-download"/>',
        outlineID: "pswp__icn-download",
      },
      onInit: (el, pswp) => {
        el.setAttribute("download", "");
        el.setAttribute("target", "_blank");
        el.setAttribute("rel", "noopener");
        el.setAttribute("title", params.downloadTitle || "Download");
        pswp.on("change", () => {
          el.href = pswp.currSlide.data.element.href;
        });
      },
    });

    // Like count display in lightbox
    lightbox.pswp.ui.registerElement({
      name: "like-count-display",
      order: 7,
      isButton: false,
      tagName: "div",
      className: "pswp__like-count",
      onInit: (el, pswp) => {
        let currentImageName = null;

        const updateLikeCount = async () => {
          currentImageName = pswp.currSlide.data?.element?.dataset?.imageName;
          if (!currentImageName) {
            el.style.display = "none";
            return;
          }

          const [{ platforms, total }, liked] = await Promise.all([
            fetchLikeData(currentImageName),
            getNativeLikeStatus(currentImageName),
          ]);

          renderLikeCount(el, total, platforms, liked, true);
          el.style.display = "flex";
        };

        // Click handler for toggling likes
        el.addEventListener("click", async (e) => {
          e.preventDefault();
          e.stopPropagation();

          if (!currentImageName) return;

          const newLiked = await toggleNativeLike(currentImageName);
          const { platforms: newPlatforms, total: newTotal } = await fetchLikeData(currentImageName);
          renderLikeCount(el, newTotal, newPlatforms, newLiked, true);

          // Also update the gallery thumbnail like count
          const galleryItem = gallery.querySelector(`[data-image-name="${currentImageName}"]`);
          if (galleryItem) {
            const thumbLikeEl = galleryItem.querySelector(".like-count");
            if (thumbLikeEl) {
              renderLikeCount(thumbLikeEl, newTotal, newPlatforms, newLiked);
            }
          }
        });

        pswp.on("change", updateLikeCount);
        updateLikeCount();
      },
    });
  });

  lightbox.on("change", () => {
    const currSlide = lightbox.pswp.currSlide;
    const id = currSlide.data?.element?.dataset?.id || currSlide.index;
    history.replaceState("", document.title, "#" + id);
  });

  lightbox.on("close", () => {
    history.replaceState("", document.title, window.location.pathname);
  });

  new PhotoSwipeDynamicCaption(lightbox, {
    mobileLayoutBreakpoint: 700,
    type: "auto",
    mobileCaptionOverlapRatio: 1,
  });

  lightbox.init();

  if (window.location.hash.substring(1).length > 0) {
    const id = window.location.hash.substring(1);
    const index = Array.from(gallery.querySelectorAll("a")).findIndex((el) => el.dataset?.id === id); 
    if (!Number.isNaN(index) && index >= 0 && index < gallery.querySelectorAll("a").length) {
      lightbox.loadAndOpen(index, { gallery });
    }
  }
}