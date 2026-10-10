import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { build } from "esbuild";
import { spawnSync } from "node:child_process";

const exported = spawnSync("uv", ["run", "python", "scripts/export-sites-contract.py"], { stdio: "inherit" });
assert.equal(exported.status, 0, "Python contract export failed");

// Same artifact layout as the official Sites Worker ESM starter; bundle imports.
await mkdir("dist/server", { recursive: true });
await mkdir("dist/.openai", { recursive: true });
const manifest = JSON.parse(await readFile(".openai/hosting.json", "utf8"));
assert(manifest.capabilities.includes("mcp"));
await build({
  entryPoints: ["worker/index.js"],
  outfile: "dist/server/index.js",
  bundle: true,
  format: "esm",
  platform: "browser",
  conditions: ["workerd", "browser"],
  target: "es2022",
});
await writeFile("dist/.openai/hosting.json", JSON.stringify(manifest, null, 2) + "\n");
// Validate the standalone module, with no node_modules or source imports needed.
const source = await readFile("dist/server/index.js", "utf8");
const module = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
assert.equal(typeof module.default.fetch, "function");
console.log(`Sites Worker built and validated (${Buffer.byteLength(source)} bytes)`);
