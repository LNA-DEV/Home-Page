/* npm run tokens:ratchet — rewrite tests/golden/css-literals.json from the
   working tree. Run it after migrating a file to tokens, in the same commit,
   so the ratchet locks the gain in. A count that goes UP shows in the diff of
   that file; that is the review point (docs/concepts/design-system.md §9). */

import { writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { countAll } from "../support/css-literals.mjs";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const counts = countAll(repo);
const target = join(repo, "tests/golden/css-literals.json");
writeFileSync(target, JSON.stringify(counts, null, 2) + "\n");

const total = {};
for (const c of Object.values(counts)) for (const [k, n] of Object.entries(c)) total[k] = (total[k] ?? 0) + n;
console.log(`${Object.keys(counts).length} files with literals:`, total);
