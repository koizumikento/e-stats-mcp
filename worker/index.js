import { McpServer, createMcpHandler, fromJsonSchema, readRequestBody } from "@modelcontextprotocol/server";
import { CfWorkerJsonSchemaValidator } from "@modelcontextprotocol/server/validators/cf-worker";
import contract from "../.sites-generated/contract.json" with { type: "json" };
import { callTool, ToolError } from "./tools.js";

const validator = new CfWorkerJsonSchemaValidator();

function redact(value, secret) {
  if (!secret) return value;
  if (typeof value === "string") return value.replaceAll(secret, "[redacted]");
  if (Array.isArray(value)) return value.map((child) => redact(child, secret));
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, child]) => [redact(key, secret), redact(child, secret)]));
  return value;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    if (origin && origin !== url.origin) return new Response("Forbidden origin", { status: 403 });
    if (url.pathname === "/identity" && request.method === "GET") {
      const user = request.headers.get("oai-authenticated-user-id");
      return user ? Response.json({ user_id: user }, { headers: { "Cache-Control": "no-store" } }) : new Response("Sign in with ChatGPT", { status: 401 });
    }
    if (url.pathname !== "/mcp") return new Response("Not found", { status: 404 });
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });

    // Only trust these headers behind Sites dispatch, never on a direct Worker URL.
    const user = request.headers.get("oai-authenticated-user-id");
    const handler = createMcpHandler(() => {
      const server = new McpServer({ name: "e-stats-mcp", version: contract.version }, { jsonSchemaValidator: validator, instructions: contract.instructions });
      for (const tool of contract.tools) {
        server.registerTool(tool.name, {
          title: tool.title,
          description: tool.description,
          inputSchema: fromJsonSchema(tool.inputSchema, validator),
          outputSchema: fromJsonSchema(tool.outputSchema, validator),
          annotations: tool.annotations,
          _meta: tool._meta,
        }, async (input) => {
          const args = Object.fromEntries(Object.entries(tool.inputSchema.properties).map(([key, schema]) => [key, Object.hasOwn(input, key) ? input[key] : schema.default]));
          try {
            // Redact after parsing too: upstream JSON/XML may encode the echoed app ID.
            const result = redact(await callTool(tool.name, args, env), env.E_STAT_APP_ID);
            const structuredContent = tool.outputSchema["x-fastmcp-wrap-result"] ? { result } : result;
            return { content: [{ type: "text", text: typeof result === "string" ? result : JSON.stringify(result) }], structuredContent };
          } catch (error) {
            return { isError: true, content: [{ type: "text", text: error instanceof ToolError ? error.message : "Tool execution failed" }] };
          }
        });
      }
      return server;
    }, { legacy: "stateless", keepAliveMs: 0, maxRequestBodySize: 1024 * 1024 });

    // Discovery is public metadata. Every other call uses the owner's e-Stat app ID.
    // Inspect only the bounded body that the SDK will also validate as JSON-RPC.
    const body = await readRequestBody(request, 1024 * 1024);
    if (body.tooLarge) return new Response("Request too large", { status: 413 });
    let message;
    try { message = JSON.parse(body.text); } catch { /* SDK reports parse errors. */ }
    if (Array.isArray(message)) return new Response("JSON-RPC batches are not supported", { status: 400 });
    if (message?.method === "tools/call") {
      if (!user) return new Response("Sign in with ChatGPT", { status: 401 });
      if (!env.E_STAT_OWNER_USER_ID) return new Response("Owner authorization is not configured", { status: 503 });
      if (user !== env.E_STAT_OWNER_USER_ID) return new Response("Forbidden", { status: 403 });
    }
    try {
      const response = await handler.fetch(new Request(request, { body: body.text }));
      response.headers.set("Cache-Control", "no-store");
      return response;
    } finally {
      await handler.close();
    }
  },
};
