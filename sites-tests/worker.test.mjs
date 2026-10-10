import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import contract from "../.sites-generated/contract.json" with { type: "json" };
import fixtures from "../.sites-generated/fixtures.json" with { type: "json" };
import { callTool } from "../worker/tools.js";
import worker from "../dist/server/index.js";

const bindings = { E_STAT_APP_ID: "fixture-only", E_STAT_OWNER_USER_ID: "owner" };
const defaults = (fixture) => ({ ...Object.fromEntries(Object.entries(contract.tools.find((tool) => tool.name === fixture.tool).inputSchema.properties).map(([key, schema]) => [key, schema.default])), ...fixture.arguments });
const redact = (value) => JSON.parse(JSON.stringify(value).replaceAll("fixture-only", "[redacted]"));

function decodeCall(call) {
  const url = new URL(call.url);
  const params = new URLSearchParams(call.method === "POST" ? call.body : url.search);
  const values = Object.fromEntries([...new Set(params.keys())].map((key) => [key, params.getAll(key).length === 1 ? params.get(key) : params.getAll(key)]));
  if (values.statsDatasSpec) values.statsDatasSpec = JSON.parse(values.statsDatasSpec);
  return { method: call.method, endpoint: url.origin + url.pathname, values };
}

async function rpc(mf, message, headers = {}) {
  const response = await mf.dispatchFetch("https://fixture.example/mcp", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25", ...headers },
    body: typeof message === "string" ? message : JSON.stringify(message),
  });
  const text = await response.text();
  const data = text.startsWith("event:") || text.startsWith("data:") ? text.split("\n").filter((line) => line.startsWith("data: ") && line.slice(6).trim()).map((line) => JSON.parse(line.slice(6))).at(-1) : text ? (() => { try { return JSON.parse(text); } catch { return text; } })() : null;
  return { response, data };
}

test("standalone artifact: Python parity, MCP SDK, authorization and errors in workerd", async (t) => {
  let current = {}, calls = [];
  const mf = new Miniflare(convertV4MiniflareOptions({
    name: "e-stats-mcp-sites-contract",
    modules: true,
    scriptPath: "dist/server/index.js",
    compatibilityDate: "2026-07-28",
    host: "127.0.0.1",
    port: 0,
    bindings,
    cacheAPI: false,
    unsafeDevRegistryPath: ".sites-generated/dev-registry",
    unsafeRegisterWorker: false,
    outboundService: async (request) => {
      assert.equal(new URL(request.url).origin, "https://api.e-stat.go.jp");
      calls.push({ method: request.method, url: request.url, body: await request.text() });
      return new Response(typeof current.upstream === "string" ? current.upstream : JSON.stringify(current.upstream ?? {}), { status: current.status ?? 200 });
    },
  }));
  t.after(() => mf.dispose());

  await t.test("initialization and discovery preserve all 13 Python definitions", async () => {
    const initialized = await rpc(mf, { jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "fixture", version: "1" } } });
    assert.equal(initialized.data.result.protocolVersion, "2025-11-25");
    assert.equal(initialized.data.result.instructions, contract.instructions);
    assert.equal(initialized.response.headers.get("mcp-session-id"), null);
    const listed = await rpc(mf, { jsonrpc: "2.0", id: 2, method: "tools/list", params: {} });
    assert.deepEqual(listed.data.result.tools, contract.tools);
    assert.equal(calls.length, 0);
    const notified = await rpc(mf, { jsonrpc: "2.0", method: "notifications/initialized" });
    assert.equal(notified.response.status, 202);
  });

  for (const fixture of fixtures.filter((item) => !item.timeout)) {
    await t.test(fixture.id, async () => {
      current = fixture;
      calls = [];
      const { response, data } = await rpc(mf, { jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: fixture.tool, arguments: fixture.arguments } }, { "oai-authenticated-user-id": "owner" });
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("Cache-Control"), "no-store");
      if (fixture.expected_error) {
        assert.equal(data.result.isError, true);
        assert.equal(data.result.content[0].text, fixture.expected_error);
      } else {
        const tool = contract.tools.find((item) => item.name === fixture.tool);
        const actual = tool.outputSchema["x-fastmcp-wrap-result"] ? data.result.structuredContent.result : data.result.structuredContent;
        assert.deepEqual(actual, redact(fixture.expected), JSON.stringify(data));
        if (typeof fixture.expected === "string") assert.equal(data.result.content[0].text, fixture.expected);
        assert(!JSON.stringify(data).includes("fixture-only"));
      }
      assert.deepEqual(calls.map(decodeCall), fixture.calls.map(decodeCall));
    });
  }

  await t.test("anonymous, service-only and other users cannot read or mutate", async () => {
    calls = [];
    for (const name of ["get_dataset", "post_dataset", "get_stats_fields"]) {
      for (const [headers, status] of [[{}, 401], [{ "OAI-Sites-Authorization": "Bearer fixture-service-token" }, 401], [{ "oai-authenticated-user-id": "other" }, 403]]) {
        const { response } = await rpc(mf, { jsonrpc: "2.0", id: 4, method: "tools/call", params: { name, arguments: { stats_data_id: "x" } } }, headers);
        assert.equal(response.status, status);
      }
    }
    assert.equal(calls.length, 0);
    const batch = await rpc(mf, [{ jsonrpc: "2.0", id: 5, method: "tools/call", params: { name: "post_dataset", arguments: { stats_data_id: "x" } } }]);
    assert.equal(batch.response.status, 400);
    assert.equal(calls.length, 0);
  });

  await t.test("identity bootstrap exposes only the signed-in caller's Site ID", async () => {
    assert.equal((await mf.dispatchFetch("https://fixture.example/identity")).status, 401);
    const response = await mf.dispatchFetch("https://fixture.example/identity", { headers: { "oai-authenticated-user-id": "owner" } });
    assert.deepEqual(await response.json(), { user_id: "owner" });
    assert.equal(response.headers.get("Cache-Control"), "no-store");
  });

  await t.test("invalid protocol, schema, origin, routing and body bounds", async () => {
    calls = [];
    assert.equal((await mf.dispatchFetch("https://fixture.example/mcp")).status, 405);
    assert.equal((await mf.dispatchFetch("https://fixture.example/nope")).status, 404);
    assert.equal((await rpc(mf, {}, { Origin: "https://evil.example" })).response.status, 403);
    assert.equal((await rpc(mf, "{broken")).response.status, 400);
    const owner = { "oai-authenticated-user-id": "owner" };
    for (const params of [{ name: "unknown", arguments: {} }, { name: "get_meta_info", arguments: {} }, { name: "get_dataset", arguments: { limit: "bad" } }, { name: "get_stats_fields", arguments: { unexpected: 1 } }]) {
      const { data } = await rpc(mf, { jsonrpc: "2.0", id: 6, method: "tools/call", params }, owner);
      assert(data.error || data.result.isError);
    }
    assert.equal(calls.length, 0);
    assert.equal((await rpc(mf, { jsonrpc: "2.0", id: 7, method: "ping" }, { "MCP-Protocol-Version": "1900-01-01" })).response.status, 400);
  });

  await t.test("SDK 2 client discovers and calls over 2026-07-28", async () => {
    const client = new Client({ name: "sites-fixture", version: "1" });
    const transport = new StreamableHTTPClientTransport(new URL("https://fixture.example/mcp"), { fetch: (url, init) => mf.dispatchFetch(String(url), { ...init, headers: { ...Object.fromEntries(new Headers(init?.headers)), "oai-authenticated-user-id": "owner" } }) });
    try {
      await client.connect(transport);
      assert.equal((await client.listTools()).tools.length, 13);
      const result = await client.callTool({ name: "get_stats_fields", arguments: {} });
      assert.deepEqual(result.structuredContent, { result: contract.fields });
    } finally { await client.close(); }
  });

  await t.test("HTTP and parser failures do not expose credentials", async () => {
    for (const fixture of [{ status: 302, upstream: "fixture-only" }, { status: 503, upstream: "fixture-only" }, { upstream: "not-json fixture-only" }, { upstream: { RESULT: { STATUS: "100", ERROR_MSG: "fixture-only" } } }]) {
      current = fixture;
      const { data } = await rpc(mf, { jsonrpc: "2.0", id: 8, method: "tools/call", params: { name: "get_stats_list", arguments: {} } }, { "oai-authenticated-user-id": "owner" });
      assert(data.result.isError);
      assert(!JSON.stringify(data).includes("fixture-only"));
    }
  });
});

test("body limits and missing owner configuration reject before API calls", async () => {
  const request = (body, headers = {}) => new Request("https://fixture.example/mcp", { method: "POST", headers, body });
  assert.equal((await worker.fetch(request(" ".repeat(1024 * 1024 + 1)), bindings)).status, 413);
  const call = JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "get_stats_fields", arguments: {} } });
  assert.equal((await worker.fetch(request(call, { "oai-authenticated-user-id": "owner" }), { E_STAT_APP_ID: "fixture-only" })).status, 503);
});

test("catalog timeout recovery matches Python for JSON and CSV", async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async () => { throw new DOMException("fixture", "TimeoutError"); };
  for (const fixture of fixtures.filter((item) => item.timeout)) assert.deepEqual(await callTool(fixture.tool, defaults(fixture), bindings), fixture.expected);
});

test("missing secrets and invalid XML fail closed", async (t) => {
  await assert.rejects(callTool("get_stats_list", { limit: 10 }, {}), /E_STAT_APP_ID/);
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  for (const text of ["<BROKEN>", '<!DOCTYPE x [<!ENTITY secret "bad">]><POST_DATASET/>']) {
    globalThis.fetch = async () => new Response(text);
    await assert.rejects(callTool("post_dataset", { process_mode: "E", stats_data_id: "x" }, bindings), /Invalid XML/);
  }
});

test("manifest contains MCP capability, no credentials or fabricated Site identity", async () => {
  const manifest = JSON.parse(await readFile("dist/.openai/hosting.json", "utf8"));
  assert.deepEqual(manifest, { d1: null, r2: null, capabilities: ["mcp"] });
});
