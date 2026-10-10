import { XMLParser, XMLValidator } from "fast-xml-parser";
import contract from "../.sites-generated/contract.json" with { type: "json" };

const BASE = "https://api.e-stat.go.jp/rest/3.0/app/";
const MAPPING = {
  search_word: "searchWord", survey_years: "surveyYears", stats_field: "statsField",
  stats_code: "statsCode", gov_code: "governmentCode", open_years: "openYears",
  stats_name_list: "statsNameList", updated_date: "updatedDate", stats_data_id: "statsDataId",
  cdtime: "cdTime", cdarea: "cdArea", dataset_name: "dataSetName",
  data_set_id: "dataSetId", open_specified: "openSpecified", dataset_id: "dataSetId",
};
const RESERVED = new Set(["appId", "dataSetId", "dataSetName", "lang", "openSpecified", "processMode", "statsDataId"]);
const parser = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "@", removeNSPrefix: true, parseTagValue: false, parseAttributeValue: false, trimValues: false, processEntities: true, htmlEntities: { amp: "&", lt: "<", gt: ">", apos: "'", quot: '"' } });

export class ToolError extends Error {}
class UpstreamTimeout extends ToolError {}

function positive(name, value) {
  if (!Number.isSafeInteger(value) || value < 1) throw new ToolError(`${name}は1以上を指定してください。`);
  return value;
}

function paramsFor(args) {
  const params = {};
  for (const [key, value] of Object.entries(args)) {
    const name = MAPPING[key] || (/^cdcat\d\d$/.test(key) ? `cdCat${key.slice(-2)}` : /^lvcat\d\d$/.test(key) ? `lvCat${key.slice(-2)}` : null);
    if (name && value) params[name] = value;
  }
  for (const key of ["start_position", "limit"]) {
    if (args[key] != null) params[key === "start_position" ? "startPosition" : key] = String(positive(key, args[key]));
  }
  return params;
}

function findResult(value) {
  if (!value || typeof value !== "object") return null;
  if (value.RESULT && typeof value.RESULT === "object") return value.RESULT;
  for (const child of Object.values(value)) {
    const result = findResult(child);
    if (result) return result;
  }
  return null;
}

function parseXML(text) {
  if (/<!DOCTYPE|<!ENTITY/i.test(text) || XMLValidator.validate(text) !== true) throw new ToolError("Invalid XML from e-Stat API");
  try { return parser.parse(text); } catch { throw new ToolError("Invalid XML from e-Stat API"); }
}

const first = (value) => Array.isArray(value) ? value[0] : value;
const xmlText = (value) => {
  const element = first(value);
  return element && typeof element === "object" ? element["#text"] || "" : element ?? "";
};

function findXMLText(value, tag) {
  if (!value || typeof value !== "object") return null;
  if (Object.hasOwn(value, tag)) return xmlText(value[tag]);
  for (const child of Object.values(value)) {
    const text = findXMLText(child, tag);
    if (text != null) return text;
  }
  return null;
}

function checkResult(payload, secret) {
  const result = findResult(payload);
  const status = String(result?.STATUS ?? "");
  if (status && !["0", "1", "2"].includes(status)) {
    const message = String(result.ERROR_MSG || "API request failed").replaceAll(secret, "[redacted]");
    throw new ToolError(`e-Stat API error ${status.replaceAll(secret, "[redacted]")}: ${message}`);
  }
}

async function request(endpoint, params, env, { method = "GET", format = "json", data = {} } = {}) {
  if (!env.E_STAT_APP_ID) throw new ToolError("E_STAT_APP_ID環境変数が設定されていません。https://www.e-stat.go.jp/api/ からアプリケーションIDを取得してください。");
  const values = new URLSearchParams();
  for (const [key, value] of Object.entries({ appId: env.E_STAT_APP_ID, ...params, ...data })) {
    for (const item of Array.isArray(value) ? value : [value]) values.append(key, item == null ? "" : String(item));
  }
  const url = new URL(endpoint, BASE);
  if (method === "GET") url.search = values.toString();
  let response, text;
  try {
    response = await fetch(url, {
      method,
      body: method === "POST" ? values : undefined,
      signal: AbortSignal.timeout(30_000),
      redirect: "manual",
    });
    text = await response.text();
  } catch (error) {
    if (["TimeoutError", "AbortError"].includes(error.name)) throw new UpstreamTimeout("e-Stat API timeout; the outcome of a dataset write may be unknown. Check get_dataset before retrying a write.");
    throw new ToolError("e-Stat API connection failed; the outcome of a dataset write may be unknown. Check get_dataset before retrying a write.");
  }
  if (!response.ok) throw new ToolError(`e-Stat API HTTP ${response.status}; check get_dataset before retrying a write.`);
  // e-Stat echoes APP_ID in PARAMETER; never return the runtime secret to callers.
  text = text.replaceAll(env.E_STAT_APP_ID, "[redacted]");
  if (format !== "json") {
    if (text.trimStart().startsWith("<")) {
      const xml = parseXML(text);
      checkResult({ RESULT: { STATUS: findXMLText(xml, "STATUS"), ERROR_MSG: findXMLText(xml, "ERROR_MSG") } }, env.E_STAT_APP_ID);
    }
    return text;
  }
  let result;
  try { result = JSON.parse(text); } catch { throw new ToolError("Invalid JSON from e-Stat API"); }
  if (!result || Array.isArray(result) || typeof result !== "object") throw new ToolError("Invalid JSON object from e-Stat API");
  checkResult(result, env.E_STAT_APP_ID);
  return result;
}

function bulkRequests(args) {
  if (args.requests != null) {
    return args.requests.map((input, i) => {
      const item = {};
      for (const [key, value] of Object.entries(input)) {
        if (value == null || value === "") continue;
        if (["startPosition", "limit"].includes(key)) {
          if (!(Number.isSafeInteger(value) || (typeof value === "string" && /^\d+$/.test(value)))) throw new ToolError(`requests[${i + 1}].${key}は1以上の整数を指定してください。`);
          item[key] = String(positive(`requests[${i + 1}].${key}`, Number(value)));
        } else item[key] = Number.isInteger(value) ? String(value) : value;
      }
      if (Object.hasOwn(item, "statsDataId") === Object.hasOwn(item, "dataSetId")) throw new ToolError(`requests[${i + 1}]にはstatsDataIdまたはdataSetIdのどちらか一方が必要です。`);
      return item;
    });
  }
  const common = {};
  if (args.start_position != null) common.startPosition = String(positive("start_position", args.start_position));
  if (args.limit != null) common.limit = String(positive("limit", args.limit));
  return [
    ...(args.stats_data_ids || []).map((statsDataId) => ({ statsDataId, ...common })),
    ...(args.dataset_ids || []).map((dataSetId) => ({ dataSetId, ...common })),
  ];
}

const list = (value) => value == null || value === "" ? [] : Array.isArray(value) ? value : [value];

function pageDataset(result, args) {
  if (args.dataset_id || (args.start_position == null && args.limit == null)) return result;
  const root = result.GET_DATASET_LIST;
  const info = root?.DATASET_LIST_INF;
  if (!info || typeof info !== "object" || Array.isArray(info)) return result;
  const start = (args.start_position || 1) - 1;
  info.DATASET_INF = list(info.DATASET_INF).slice(start, args.limit == null ? undefined : start + args.limit);
  info.NUMBER = info.DATASET_INF.length;
  if (!Object.hasOwn(root, "PARAMETER")) root.PARAMETER = {};
  if (root.PARAMETER && typeof root.PARAMETER === "object" && !Array.isArray(root.PARAMETER)) {
    if (args.start_position != null) root.PARAMETER.START_POSITION = String(args.start_position);
    if (args.limit != null) root.PARAMETER.LIMIT = String(args.limit);
  }
  return result;
}

function parseDataset(text) {
  const parsed = parseXML(text);
  const root = Object.entries(parsed).find(([key, value]) => !key.startsWith("?") && value && typeof value === "object" && !Array.isArray(value))?.[1] || {};
  const children = (value) => value && typeof value === "object" ? Object.entries(value).filter(([key]) => !key.startsWith("@") && key !== "#text") : [];
  const nested = (value) => Object.fromEntries(children(value).map(([key, child]) => {
    const element = Array.isArray(child) ? child.at(-1) : child;
    return [key.toLowerCase(), children(element).length ? nested(element) : xmlText(element)];
  }));
  const resultElement = first(root.RESULT);
  const result = resultElement ? { status: xmlText(resultElement.STATUS), error_message: xmlText(resultElement.ERROR_MSG), date: xmlText(resultElement.DATE) } : {};
  const info = first(root.REGIST_INF);
  const dataset = info ? Object.fromEntries(Object.entries({ mode: info["@mode"] || "", dataset_id: xmlText(info.DATASET_ID), stats_data_id: xmlText(info.STATS_DATA_ID), public_state: xmlText(info.PUBLIC_STATE), total_number: xmlText(info.TOTAL_NUMBER) }).filter(([, value]) => value !== "")) : {};
  return { result, parameter: nested(first(root.PARAMETER)), dataset };
}

function recovery(code, query, count) {
  const next = [];
  if (query) next.push({ tool: "get_stats_list", arguments: { search_word: query, limit: 10 }, reason: "統計表候補を先に探索し、stats_codeを特定する" });
  next.push({ tool: "get_data_catalog", arguments: { stats_code: "00200524", limit: 1 }, reason: "stats_code等で対象統計を絞ってデータカタログを取得する" });
  return { code, message: "e-Stat data catalog search timed out or matched too many results. Narrow the query before retrying.", retryable: true, matched_count_hint: count, suggested_next_calls: next };
}

function stringify(value) {
  if (value == null) return "";
  if (Array.isArray(value)) return value.map(stringify).join(";");
  if (typeof value === "object") return Object.entries(flatten(value)).map(([key, child]) => `${key}=${child}`).join(";");
  return typeof value === "boolean" ? value ? "True" : "False" : String(value);
}

function flatten(value, prefix = "") {
  if (value && typeof value === "object" && !Array.isArray(value)) return Object.fromEntries(Object.entries(value).flatMap(([key, child]) => Object.entries(flatten(child, prefix ? `${prefix}.${key}` : key))));
  return { [prefix]: Array.isArray(value) ? value.map(stringify).filter((item) => item !== "").join(";") : stringify(value) };
}

function catalogCSV(result) {
  const rows = list(result.GET_DATA_CATALOG?.DATA_CATALOG_LIST_INF?.DATA_CATALOG_INF).map((row) => flatten(row));
  if (!rows.length) return "";
  const columns = [...new Set(rows.flatMap(Object.keys))].sort();
  const escape = (value) => /[",\n\r]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
  return [columns, ...rows.map((row) => columns.map((key) => row[key] ?? ""))].map((row) => row.map(escape).join(",")).join("\n") + "\n";
}

export async function callTool(name, args, env) {
  if (name === "get_stats_fields") return contract.fields;
  if (name === "search_stats_by_keyword") return callTool("get_stats_list", { search_word: args.keyword, limit: args.limit ?? 20 }, env);
  if (name === "get_stats_data_bulk") {
    const requests = bulkRequests(args);
    if (!requests.length) throw new ToolError("requests、stats_data_ids、dataset_idsのいずれかを指定してください。");
    return request("json/getStatsDatas", { lang: "J" }, env, { method: "POST", data: { statsDatasSpec: JSON.stringify(requests) } });
  }
  const params = paramsFor(args);
  if (name === "post_dataset") {
    if (!["E", "D"].includes(args.process_mode)) throw new ToolError("process_modeは'E'または'D'を指定してください。");
    if (args.process_mode === "E" && !args.stats_data_id) throw new ToolError("process_mode='E'ではstats_data_idが必要です。");
    if (args.process_mode === "D" && !args.data_set_id) throw new ToolError("process_mode='D'ではdata_set_idが必要です。");
    const reserved = Object.keys(args.conditions || {}).filter((key) => RESERVED.has(key)).sort();
    if (reserved.length) throw new ToolError(`conditionsに予約パラメータは指定できません: ${reserved.join(", ")}`);
    return parseDataset(await request("postDataset", { ...params, processMode: args.process_mode, ...args.conditions }, env, { method: "POST", format: "xml" }));
  }
  if (name === "get_dataset") {
    return pageDataset(await request("json/refDataset", args.dataset_id ? { dataSetId: args.dataset_id } : {}, env), args);
  }
  if (name.startsWith("get_data_catalog")) {
    let result;
    try { result = await request("json/getDataCatalog", params, env); }
    catch (error) {
      if (!(error instanceof UpstreamTimeout)) throw error;
      return { isError: true, structuredContent: { error: recovery("UPSTREAM_TIMEOUT_QUERY_TOO_BROAD", args.search_word, null) }, content: [{ type: "text", text: "Data catalog query is too broad. Try get_stats_list first, then retry get_data_catalog with stats_code or another narrowing parameter." }] };
    }
    const rawCount = result.GET_DATA_CATALOG?.DATA_CATALOG_LIST_INF?.NUMBER;
    const count = rawCount == null || (typeof rawCount === "string" && !/^[+-]?\d+$/.test(rawCount.trim())) ? NaN : Number(rawCount);
    const broad = count >= 1000 && params.searchWord && !["statsCode", "statsField", "governmentCode", "surveyYears", "openYears", "statsNameList", "updatedDate"].some((key) => Object.hasOwn(params, key));
    const guidance = broad ? recovery("DATA_CATALOG_QUERY_TOO_BROAD", args.search_word, Math.trunc(count)) : null;
    if (name.endsWith("_csv")) {
      const csv = catalogCSV(result);
      return guidance ? { csv, MCP_GUIDANCE: guidance } : csv;
    }
    if (guidance) result.MCP_GUIDANCE = guidance;
    return result;
  }
  params.lang = "J";
  if (name.startsWith("get_meta_info") || name.startsWith("get_stats_data")) params.statsDataId = args.stats_data_id;
  if (name.startsWith("get_stats_list")) params.limit = String(Math.min(positive("limit", args.limit ?? 10), 100));
  if (name.startsWith("get_stats_data")) {
    params.limit = String(positive("limit", args.limit ?? 100));
    if (args.section_header_flg != null) params.sectionHeaderFlg = args.section_header_flg ? "1" : "2";
    if (args.cnt_get_flg) params.cntGetFlg = "Y";
  }
  const endpoint = { get_stats_list: "json/getStatsList", get_stats_list_csv: "getSimpleStatsList", get_meta_info: "json/getMetaInfo", get_meta_info_csv: "getSimpleMetaInfo", get_stats_data: "json/getStatsData", get_stats_data_csv: "getSimpleStatsData" }[name];
  if (!endpoint) throw new ToolError("Unknown tool");
  return request(endpoint, params, env, { format: name.endsWith("_csv") ? "csv" : "json" });
}
