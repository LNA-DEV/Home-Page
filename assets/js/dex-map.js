/* Species distribution map.

   The default map is entirely local: a Natural Earth world outline drawn as
   GeoJSON instead of raster tiles, the species' simplified iNaturalist range on
   top, then any hand-entered sighting pins. That means opening a species page
   makes no third-party request at all, which matters for the Tor onion build —
   and for a range map, continents are the useful level of detail anyway.

   Pressing "detailed map" is the explicit opt-in that swaps the drawn world for
   OpenStreetMap tiles plus the GBIF occurrence-density overlay. The range stays
   on top in both modes, since comparing the modelled range against the actual
   observations is the interesting part.

   Note on the antimeridian: a raster base layer repeats itself forever, but a
   GeoJSON world is drawn exactly once. So every vector layer here — land,
   borders and range alike — is drawn at three longitude offsets. Duplicating
   only the range (as this did originally) leaves its copies floating over empty
   ocean at the edges of a zoomed-out map. */
(function () {
  const container = document.querySelector("[data-dex-map]");
  if (!container || typeof L === "undefined") return;

  const canvas = container.querySelector("[data-dex-map-canvas]");
  if (!canvas) return;

  const cssVar = (name, fallback) => {
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || fallback;
  };

  const colors = {
    land: cssVar("--dex-map-land", "#d9d4c7"),
    landEdge: cssVar("--dex-map-land-edge", "#b4ad9c"),
    border: cssVar("--dex-map-border", "#a8a091"),
    range: cssVar("--dex-map-range", "#2f7d5b"),
    water: cssVar("--dex-map-water", "#dbe6ec"),
    sighting: cssVar("--dex-map-sighting", "#d97706"),
  };

  /* Longitude offsets every vector layer is drawn at. Content therefore spans
     -540°..540°, while panning is capped at ±360° below — so there is always a
     further copy past the edge of the view and never a blank margin. */
  const COPIES = [-360, 0, 360];
  const PAN_LIMIT = 360;

  const map = L.map(canvas, {
    center: [30, 10],
    zoom: 1,
    minZoom: 1,
    /* Fractional zoom. With integer-only zoom, a container wider than 512px
       forces a global range down to zoom 1, where one world is 512px and the
       leftover width fills with the ±360° copies — the map then reads as
       repeating wallpaper. Fractional levels let exactly one world fill the
       frame instead. */
    zoomSnap: 0,
    maxZoom: 7,
    zoomControl: true,
    scrollWheelZoom: false,
    attributionControl: false,
    /* worldCopyJump snaps the view back to the middle copy when you pan past
       the antimeridian. That snap only earns its keep when the overlays exist
       in one copy alone; here everything is drawn in all three, so it would be
       a visible jump for no gain. */
    worldCopyJump: false,
    /* Longitude only. Web Mercator already stops at ±85.05°, so a tighter
       latitude bound would make the viewport taller than the bounds at low
       zoom and leave viscosity fighting every drag. ±90 can never be
       exceeded, so the latitude half stays inert. */
    maxBounds: [
      [-90, -PAN_LIMIT],
      [90, PAN_LIMIT],
    ],
    maxBoundsViscosity: 1,
    /* Three copies of the Natural Earth borders is a few hundred paths; canvas
       keeps panning smooth where SVG would start to struggle on a phone. */
    preferCanvas: true,
  });
  /* The zoom at which a single world exactly spans the container. Used as the
     floor, so the default view never shows more than 360° of longitude — the
     copies stay available for panning across the antimeridian. */
  function worldFitZoom() {
    const width = canvas.clientWidth || 0;
    return width > 0 ? Math.log2(width / 256) : 1;
  }
  const applyMinZoom = () => map.setMinZoom(Math.max(1, worldFitZoom()));
  applyMinZoom();
  map.on("resize", applyMinZoom);

  // Click to take control of the wheel, leave to give it back to the page.
  map.on("click", () => map.scrollWheelZoom.enable());
  map.on("mouseout", () => map.scrollWheelZoom.disable());

  /* Three groups. "Detailed map" swaps out only `baseLayers`; the range and
     the ocean mask stay, so the range means the same thing in both modes. */
  const baseLayers = L.layerGroup().addTo(map);
  const maskLayers = L.layerGroup().addTo(map);
  const rangeLayers = L.layerGroup().addTo(map);
  const rangeCopies = [];
  const maskCopies = [];
  let rangeBounds = null;
  let detailed = false;

  /* OpenStreetMap's own sea colour. The mask has to match whatever is beneath
     it, so it changes with the mode. */
  const OSM_SEA = "#aad3df";
  /* The mask is a 110m coastline. That agrees exactly with the drawn world,
     which is the same data — but over OSM tiles it drifts from the real
     coastline as you zoom, so past this point it fades out and you see the
     unmasked model over real geography. */
  const MASK_FULL_ZOOM = 5;
  const MASK_GONE_ZOOM = 7;

  function maskOpacity() {
    if (!detailed) return 1;
    const zoom = map.getZoom();
    if (zoom <= MASK_FULL_ZOOM) return 1;
    if (zoom >= MASK_GONE_ZOOM) return 0;
    return (MASK_GONE_ZOOM - zoom) / (MASK_GONE_ZOOM - MASK_FULL_ZOOM);
  }

  function applyMaskStyle() {
    const fillOpacity = maskOpacity();
    for (const layer of maskCopies) {
      layer.setStyle({
        stroke: false,
        fillColor: detailed ? OSM_SEA : colors.water,
        fillOpacity,
      });
    }
  }
  map.on("zoomend", applyMaskStyle);

  /* These are independent fetches that can finish in any order, and a shared
     renderer paints in the order layers arrive — which is how the range first
     ended up *underneath* the land, visible only over the sea. Panes pin the
     stacking order regardless of who wins the race:

       land   the drawn continents
       range  the species polygon, over the land
       ocean  water repainted on top, which clips the range back to the coast
       lines  country borders last, so nothing hides them

     All sit above tilePane, so the range still reads over OSM tiles. */
  const PANES = { land: 410, range: 420, ocean: 430, lines: 440 };
  const renderers = {};
  for (const [name, zIndex] of Object.entries(PANES)) {
    map.createPane(`dex-${name}`).style.zIndex = zIndex;
    renderers[name] = L.canvas({ pane: `dex-${name}` });
  }

  const loadJson = (url) =>
    fetch(url)
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null);

  function shifted(geojson, offset) {
    const clone = JSON.parse(JSON.stringify(geojson));
    const walk = (coords) => {
      if (typeof coords[0] === "number") {
        coords[0] += offset;
      } else {
        coords.forEach(walk);
      }
    };
    if (clone.geometry) walk(clone.geometry.coordinates);
    if (clone.features) {
      clone.features.forEach((feature) => {
        if (feature.geometry) walk(feature.geometry.coordinates);
      });
    }
    return clone;
  }

  /* Draw one GeoJSON document once per copy. Returns the layers in COPIES
     order, so the caller can pick the unshifted one for bounds. */
  function addCopies(geojson, style, group, renderer) {
    return COPIES.map((offset) => {
      const source = offset === 0 ? geojson : shifted(geojson, offset);
      return L.geoJSON(source, { interactive: false, style, renderer }).addTo(group);
    });
  }

  function rangeStyle(overTiles) {
    return {
      color: colors.range,
      weight: overTiles ? 1.5 : 1,
      fillColor: colors.range,
      // Lighter over OSM, so the map underneath stays readable.
      fillOpacity: overTiles ? 0.18 : 0.35,
    };
  }


  /* Total area of a range, in square degrees. Only used to decide whether the
     ocean mask is appropriate — see below. */
  function rangeArea(geojson) {
    let total = 0;
    const ringArea = (ring) => {
      let sum = 0;
      for (let i = 0; i < ring.length - 1; i += 1) {
        sum += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
      }
      return Math.abs(sum) / 2;
    };
    const walk = (geometry) => {
      if (!geometry) return;
      const polygons =
        geometry.type === "MultiPolygon"
          ? geometry.coordinates
          : geometry.type === "Polygon"
            ? [geometry.coordinates]
            : [];
      for (const polygon of polygons) total += ringArea(polygon[0]);
    };
    if (geojson.geometry) walk(geojson.geometry);
    if (geojson.features) geojson.features.forEach((f) => walk(f.geometry));
    return total;
  }

  /* Below this, masking does more harm than good. The mask exists to trim
     iNaturalist's ocean over-prediction on wide-ranging species; a local
     endemic has no such problem, and the base map is Natural Earth 110m, which
     omits small islands entirely — so the mask would have no hole to leave and
     would paint the whole range away. The Galapagos giant tortoise (3 sq deg)
     is the case that exposed this. */
  const MASK_MIN_RANGE_AREA = 60;

  const worldUrl = container.dataset.world;
  const bordersUrl = container.dataset.borders;
  const oceanUrl = container.dataset.ocean;
  const rangeUrl = container.dataset.range;
  const isMarine = container.dataset.marine === "1";
  let maskAllowed = !isMarine;

  const worldReady = worldUrl
    ? loadJson(worldUrl).then((data) => {
        if (!data) return;
        addCopies(
          data,
          {
            color: colors.landEdge,
            weight: 0.6,
            fillColor: colors.land,
            fillOpacity: 1,
          },
          baseLayers,
          renderers.land
        );
      })
    : Promise.resolve();

  /* iNaturalist's geomodel is a thresholded prediction raster, so for a
     wide-ranging terrestrial species its polygon spills well out to sea —
     wild boar genuinely covers the north Pacific in the source data. Painting
     the ocean back over the range clips it to the coastline. Marine species
     opt out, since for them the water is the whole point. */
  const oceanData = oceanUrl && !isMarine ? loadJson(oceanUrl) : Promise.resolve(null);

  const bordersReady = bordersUrl
    ? loadJson(bordersUrl).then((data) => {
        if (!data) return;
        addCopies(
          data,
          { color: colors.border, weight: 0.5, fill: false },
          baseLayers,
          renderers.lines
        );
      })
    : Promise.resolve();

  const rangeReady = rangeUrl
    ? loadJson(rangeUrl).then((data) => {
        if (!data) return;
        const layers = addCopies(data, rangeStyle(false), rangeLayers, renderers.range);
        rangeCopies.push(...layers);
        const bounds = layers[COPIES.indexOf(0)].getBounds();
        if (bounds.isValid()) rangeBounds = bounds;
        if (rangeArea(data) < MASK_MIN_RANGE_AREA) maskAllowed = false;
      })
    : Promise.resolve();

  let sightings = [];
  try {
    sightings = JSON.parse(container.dataset.sightings || "[]");
  } catch (err) {
    sightings = [];
  }

  const pinIcon = L.divIcon({
    className: "dex-map-pin",
    html: '<span class="dex-map-pin__dot"></span>',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });

  const sightingBounds = [];
  for (const spot of sightings) {
    const marker = L.marker([spot.lat, spot.lng], { icon: pinIcon }).addTo(map);
    const label = [spot.label, spot.date].filter(Boolean).join(" · ");
    marker.bindPopup(label || container.dataset.labelSighting || "");
    sightingBounds.push([spot.lat, spot.lng]);
  }

  /* Ocean goes on only once the range has been measured, so a species too
     small to mask never gets covered up. */
  const oceanReady = Promise.all([oceanData, rangeReady]).then(([data]) => {
    if (!data || !maskAllowed) return;
    maskCopies.push(
      ...addCopies(
        data,
        { stroke: false, fillColor: colors.water, fillOpacity: 1 },
        maskLayers,
        renderers.ocean
      )
    );
    applyMaskStyle();
  });

  Promise.all([worldReady, oceanReady, bordersReady, rangeReady]).then(() => {
    if (sightingBounds.length) {
      const bounds = L.latLngBounds(sightingBounds);
      if (rangeBounds) bounds.extend(rangeBounds);
      map.fitBounds(bounds.pad(0.4), { maxZoom: 6 });
    } else if (rangeBounds) {
      map.fitBounds(rangeBounds.pad(0.15));
    }
  });

  /* --- opt-in third-party layers ------------------------------------------ */
  const detailButton = document.querySelector("[data-dex-map-detail]");
  if (!detailButton) return;

  let tiles = null;
  let density = null;
  let attribution = null;
  const taxonKey = container.dataset.gbifKey;

  detailButton.addEventListener("click", () => {
    if (!detailed) {
      // The drawn world needs no attribution control (it is credited in the
      // caption), but OSM and GBIF do, so one is created when they appear.
      attribution = L.control.attribution({ prefix: false }).addTo(map);
      tiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 12,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);
      if (taxonKey) {
        density = L.tileLayer(
          "https://api.gbif.org/v2/map/occurrence/density/{z}/{x}/{y}@1x.png" +
            "?srs=EPSG%3A3857&style=classic.poly&bin=hex&hexPerTile=110&taxonKey=" +
            encodeURIComponent(taxonKey),
          {
            opacity: 0.7,
            maxZoom: 14,
            attribution:
              'Occurrences: <a href="https://www.gbif.org/species/' +
              encodeURIComponent(taxonKey) +
              '">GBIF</a>',
          }
        ).addTo(map);
      }
      // Only the drawn world is swapped out — the range polygon and its ocean
      // mask both stay, so the range still means "on land" in this mode too.
      map.removeLayer(baseLayers);
      for (const layer of rangeCopies) layer.setStyle(rangeStyle(true));
      map.setMaxZoom(14);
      detailButton.classList.add("is-active");
      detailed = true;
      applyMaskStyle();
    } else {
      if (tiles) map.removeLayer(tiles);
      if (density) map.removeLayer(density);
      if (attribution) map.removeControl(attribution);
      tiles = density = attribution = null;
      map.addLayer(baseLayers);
      for (const layer of rangeCopies) layer.setStyle(rangeStyle(false));
      if (map.getZoom() > 7) map.setZoom(7);
      map.setMaxZoom(7);
      detailButton.classList.remove("is-active");
      detailed = false;
      applyMaskStyle();
    }
  });
})();
