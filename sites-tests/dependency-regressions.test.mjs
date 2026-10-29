import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { z } from "zod";
import { CompleteResultSchema } from "@modelcontextprotocol/core";

function runOfflineFixture(source) {
  const child = spawnSync(process.execPath, ["--input-type=module", "-e", source], { cwd: process.cwd(), encoding: "utf8", timeout: 5000 });
  assert.ifError(child.error);
  assert.equal(child.signal, null);
  assert.equal(child.status, 0, child.stderr);
}

test("Zod rejects oversized malformed collections before walking their elements", () => {
  let visited = 0;
  const element = z.preprocess((value) => { visited++; return value; }, z.string());
  const cases = [
    [z.array(element).max(2), Array(32).fill(null)],
    [z.array(element).length(2), Array(32).fill(null)],
    [z.set(element).max(2), new Set([1, 2, 3])],
    [z.map(element, element).max(2), new Map([[1, 1], [2, 2], [3, 3]])],
  ];
  for (const [schema, value] of cases) {
    visited = 0;
    const result = schema.safeParse(value);
    assert.equal(result.success, false);
    assert.equal(result.error.issues.length, 1);
    assert.equal(result.error.issues[0].code, "too_big");
    assert.equal(visited, 0);
  }
  assert.deepEqual(z.array(z.string()).max(2).parse(["a", "b"]), ["a", "b"]);
});

test("the production MCP SDK uses the bounded Zod collection parser", () => {
  const result = CompleteResultSchema.safeParse({ completion: { values: Array(101).fill(null) } });
  assert.equal(result.success, false);
  assert.equal(result.error.issues.length, 1);
  assert.equal(result.error.issues[0].code, "too_big");
  assert.deepEqual(result.error.issues[0].path, ["completion", "values"]);
});

test("undici contains an excessive-content-encoding failure without crashing its process", () => {
  // A subprocess observes an uncaught stream error as failure instead of killing
  // the whole test runner. The only peer is a tiny loopback TCP fixture.
  const source = `
    import assert from 'node:assert/strict';
    import { createServer } from 'node:net';
    import { once } from 'node:events';
    import { fetch, Agent } from 'undici';
    const server = createServer(socket => socket.once('data', () => socket.end(
      'HTTP/1.1 200 OK\\r\\nContent-Encoding: gzip,gzip,gzip,gzip,gzip,gzip\\r\\nContent-Length: 10\\r\\nConnection: close\\r\\n\\r\\n'
    )));
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    const agent = new Agent();
    try {
      await assert.rejects(fetch('http://127.0.0.1:' + server.address().port, { dispatcher: agent }));
      await new Promise(resolve => setTimeout(resolve, 20));
    } finally {
      await agent.close();
      server.close();
      await once(server, 'close');
    }
  `;
  runOfflineFixture(source);
});

test("undici reports a decompressed response limit as a request error", () => {
  runOfflineFixture(`
    import assert from 'node:assert/strict';
    import { createServer } from 'node:http';
    import { once } from 'node:events';
    import { gzipSync } from 'node:zlib';
    import { Client, interceptors } from 'undici';
    const server = createServer((request, response) => {
      response.writeHead(200, { 'Content-Encoding': 'gzip' });
      response.end(gzipSync(Buffer.alloc(4096, 65)));
    });
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    const client = new Client('http://127.0.0.1:' + server.address().port).compose(
      interceptors.decompress(), interceptors.dump({ maxSize: 32 })
    );
    try {
      const response = await client.request({ method: 'GET', path: '/' });
      await assert.rejects(response.body.text(), { name: 'AbortError' });
    } finally {
      await client.close();
      server.close();
      await once(server, 'close');
    }
  `);
});
