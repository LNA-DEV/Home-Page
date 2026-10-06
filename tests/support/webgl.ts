/* A browser without WebGL2 — a hardened Firefox (webgl.disabled), Tor Browser
 * at its stricter levels, an old phone. The page then sees no "webgl2"
 * context, which is the one thing basemap.js checks before it loads MapLibre. */

import type { Page } from "@playwright/test";

export async function withoutWebGL2(page: Page) {
  await page.addInitScript(() => {
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, type: string, ...rest: unknown[]) {
      return type === "webgl2" ? null : (getContext as (...a: unknown[]) => unknown).call(this, type, ...rest);
    } as typeof getContext;
  });
}
