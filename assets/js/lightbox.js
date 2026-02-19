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

    // Info button for EXIF details popup
    lightbox.pswp.ui.registerElement({
      name: "info-button",
      order: 9,
      isButton: false,
      tagName: "button",
      className: "pswp__button pswp__button--info",
      html: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>',
      onInit: (el) => {
        el.setAttribute("title", params.infoTitle || "Photo info");
        el.style.cursor = "pointer";

        el.addEventListener("click", (e) => {
          e.stopPropagation();

          const currSlide = lightbox.pswp?.currSlide;
          if (!currSlide) return;

          const captionEl = currSlide.data?.element?.querySelector(".pswp-caption-content");
          if (!captionEl) return;

          // Get EXIF data from caption
          const exifItems = captionEl.querySelectorAll(".exif-item");
          const gearItems = captionEl.querySelectorAll(".gear-item");
          const copyright = captionEl.querySelector(".caption-copyright")?.textContent || "";
          const artist = captionEl.querySelector(".caption-artist")?.textContent || "";
          const keywords = captionEl.querySelector(".caption-keywords")?.textContent || "";

          // Create or get existing popup
          let popup = document.querySelector(".pswp-info-popup");
          if (!popup) {
            popup = document.createElement("div");
            popup.className = "pswp-info-popup";
            document.body.appendChild(popup);

            // Close on click outside or pressing Escape
            popup.addEventListener("click", (evt) => {
              if (evt.target === popup) {
                popup.classList.remove("visible");
                document.documentElement.style.overflow = "";
                document.body.style.overflow = "";
              }
            });
            document.addEventListener("keydown", (evt) => {
              if (evt.key === "Escape" && popup.classList.contains("visible")) {
                popup.classList.remove("visible");
                document.documentElement.style.overflow = "";
                document.body.style.overflow = "";
              }
            });
          }

          // Build popup content
          let content = '<div class="pswp-info-popup-content">';
          content += '<button class="pswp-info-popup-close" aria-label="Close">&times;</button>';

          if (exifItems.length === 0 && gearItems.length === 0 && !copyright && !artist && !keywords) {
            content += '<p class="pswp-info-empty">No data available</p>';
          }

          if (exifItems.length > 0) {
            content += '<div class="pswp-info-section"><h4>Settings</h4><div class="pswp-info-grid">';
            const labels = ["Focal Length", "Aperture", "Shutter Speed", "ISO"];
            exifItems.forEach((item, i) => {
              content += `<div class="pswp-info-item"><span class="pswp-info-label">${labels[i] || ""}</span><span class="pswp-info-value">${item.textContent}</span></div>`;
            });
            content += '</div></div>';
          }

          if (gearItems.length > 0) {
            content += '<div class="pswp-info-section"><h4>Gear</h4><div class="pswp-info-gear">';
            const gearLabels = ["Camera", "Lens"];
            gearItems.forEach((item, i) => {
              content += `<div class="pswp-info-item"><span class="pswp-info-label">${gearLabels[i] || ""}</span><span class="pswp-info-value">${item.textContent}</span></div>`;
            });
            content += '</div></div>';
          }

          if (keywords) {
            content += '<div class="pswp-info-section"><h4>Tags</h4><div class="pswp-info-tags">';
            // Split by comma or semicolon
            keywords.split(/[,;]/).map(k => k.trim()).filter(k => k).forEach((keyword) => {
              content += `<span class="pswp-info-tag">${keyword}</span>`;
            });
            content += '</div></div>';
          }

          if (copyright || artist) {
            content += '<div class="pswp-info-section"><h4>Copyright</h4>';
            if (artist) {
              content += `<p class="pswp-info-artist">${artist}</p>`;
            }
            if (copyright) {
              content += `<p class="pswp-info-copyright">${copyright}</p>`;
            }
            content += '</div>';
          }

          content += '</div>';
          popup.innerHTML = content;

          // Add close button handler
          popup.querySelector(".pswp-info-popup-close").addEventListener("click", () => {
            popup.classList.remove("visible");
            document.documentElement.style.overflow = "";
            document.body.style.overflow = "";
          });

          popup.classList.add("visible");
          document.documentElement.style.overflow = "hidden";
          document.body.style.overflow = "hidden";
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
    // Close info popup when lightbox closes
    const popup = document.querySelector(".pswp-info-popup");
    if (popup) {
      popup.classList.remove("visible");
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
    }
  });

  // Caption only shows title now, EXIF details moved to info popup
  new PhotoSwipeDynamicCaption(lightbox, {
    mobileLayoutBreakpoint: 700,
    type: "auto",
    mobileCaptionOverlapRatio: 1,
    captionContent: (slide) => {
      const titleEl = slide.data.element?.querySelector(".caption-title");
      return titleEl ? titleEl.textContent : "";
    },
  });

  lightbox.on('openingAnimationStart', () => {
    const img = lightbox.pswp.currSlide.container.querySelector('.pswp__img');
    if (img) {
      img.style.clipPath = 'inset(0 round 4px)';
      img.style.transition = 'clip-path 333ms cubic-bezier(.4,0,.22,1)';
      requestAnimationFrame(() => { img.style.clipPath = 'inset(0 round 0)'; });
    }
  });

  lightbox.on('closingAnimationStart', () => {
    const img = lightbox.pswp.currSlide.container.querySelector('.pswp__img');
    if (img) {
      img.style.transition = 'clip-path 333ms cubic-bezier(.4,0,.22,1)';
      img.style.clipPath = 'inset(0 round 4px)';
    }
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