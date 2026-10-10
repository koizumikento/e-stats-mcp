import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

// Archive only the standalone Worker and hosting manifest, never local secrets.
const archive = ".sites-generated/e-stats-mcp-sites.tar.gz";
const manifest = JSON.parse(await readFile("dist/.openai/hosting.json", "utf8"));
assert(manifest.capabilities.includes("mcp"));
const result = spawnSync("tar", ["-czf", archive, "-C", "dist", "server/index.js", ".openai/hosting.json"], { stdio: "inherit" });
assert.equal(result.status, 0, "Sites archive creation failed");
console.log(`${archive} sha256=${createHash("sha256").update(await readFile(archive)).digest("hex")}`);
