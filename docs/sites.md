# Sites Worker

SitesのCloudflare Workerで既存13ツールを実行する追加runtimeです。Python library、
CLI、stdioは変更していません。別backend、tunnel、D1、R2は不要です。

## Build / test / package

Node.js 24、Python 3.11以上、uv、npm、tarを使用します。リポジトリrootで実行します。

```sh
uv sync --frozen
npm ci
uv run pytest -q
uv run ruff check .
uv run mypy e_stats_mcp
npm run build
npm test
npm run package
```

`npm run build` はPythonからツール名・description・input/output schema・annotations・
分野コードとmock HTTP fixtureの期待値を `.sites-generated/` に生成し、公式MCP SDK
2.3.1とXML parserを単一ESMにbundleします。Pythonでツール契約を変更した場合も、
次のbuild/testでWorker側の不足や差分が検出されます。実APIへの接続は不要です。

公式Sites Worker ESM starterと同じartifact layoutです。

```text
dist/
  server/index.js
  .openai/hosting.json
```

`npm test` はこの生成済みbundleをMiniflare/workerdで実行します。HTTP送信先は
全てmockに固定し、SDK client、2025-11-25 initialization、2026-07-28 discovery/call、
所有者認可、JSON/CSV/XML、camelCase parameter、ローカルページング、catalog復旧、
入力・APIエラーを検証します。認証ヘッダはfixtureであり、Sites OAuthの実証ではありません。
Miniflareは修正済みの5 alphaをdev用に固定し、公式v4 option変換helperを使用します。
runtime bundleにはMiniflareやPythonを含めません。

`npm run package` はこの2ファイルだけを
`.sites-generated/e-stats-mcp-sites.tar.gz` に格納し、SHA-256を出力します。
source、依存環境、fixture、`.env`、secret値はarchiveに含めません。

## Hosting / identity / secrets

`.openai/hosting.json` は `capabilities: ["mcp"]`、未使用の `d1` / `r2: null` を宣言します。
レビュー段階では架空の `project_id` を入れていません。実配備時にはSitesから返された
IDをsource manifestに保存してから再build/packageします。既存Siteを更新する場合は
そのID・audience・全manifest field・storage bindingを保持してください。

secret名のみを [.env.example](../.env.example) に記載しています。

| Runtime secret | Purpose |
| --- | --- |
| `E_STAT_APP_ID` | 所有者のe-Stat application ID。全API callでserver側のみ使用 |
| `E_STAT_OWNER_USER_ID` | このSiteの所有者の `oai-authenticated-user-id`。別SiteのIDやemailを使用しない |

SitesがOAuthと接続認証を担当します。このWorkerはOAuthや独自sessionを実装しません。
`GET /identity` はSitesでサインインした呼出者自身のSite内user IDだけを返し、設定時に
使用します。app ID、email、他者のIDは返しません。両secretはSitesのnative secret設定で
登録し、source・manifest・browser bundle・log・モデルpromptに値を載せないでください。

`POST /mcp` はstatelessです。`initialize`、`server/discover`、`tools/list` は公開契約のみを
返し、APIに接続しません。全 `tools/call` はSitesのidentityが必要です。未認証はHTTP 401、
所有者不一致は403、owner secret未設定は503です。所有者のapp IDに属するdatasetの
参照・登録・更新・削除は、その所有者だけに許可します。サービス用
`OAI-Sites-Authorization` tokenだけではユーザー権限になりません。

identity headerはSites dispatchが付与する信頼済み値という前提です。直接workers.devや
別reverse proxyに公開すると任意のcallerがheaderを偽装できるため、このartifactの
公開入口はSites dispatchだけにしてください。private Siteで運用し、検証目的でも
既存Siteのaudienceを変更しないでください。Originがある場合は同一originのみ許可します。

## Deploy with the official Sites workflow

このPRはsourceのみで、Siteを作成・配備・plugin登録していません。配備が承認された後の手順です。
`<sites-plugin-root>` は公式Sites pluginの `scripts/` を含むinstalled directoryです。

1. 新規の場合はnative `create_site` でprivate Siteを作り、返されたIDを
   `node <sites-plugin-root>/scripts/set-project-id.mjs --project-id <returned-id>` で保存します。
   既存の場合は `get_site` と `create_source_repository_write_credential`、公式source helperで
   正しいsource checkoutを開き、この変更を反映します。credentialはstdinだけに渡します。
2. 上記build/testを実行し、official source helperへ残るcommand配列
   `[["npm", "run", "build"]]` と絶対 `archivePath` を渡してsource同期・packageします。
   `node <sites-plugin-root>/scripts/site-workflow.mjs --project-id <returned-id>` に対し、
   credential・既存sourceのopening result・commands・archivePathをstdin JSONで渡します。
   helperが返したproject ID・commit SHA・archiveをそのまま使用してください。
3. private audienceを保持し、native `save_version_and_deploy_private` を使用します。
   未提供なら `save_site_version` と `deploy_private_site_version` を順番に使用します。
   tokenやsecretをmanifestに追加しません。
4. 所有者としてSiteにサインインし `/identity` を開き、native Sites secret設定で
   `E_STAT_OWNER_USER_ID` と `E_STAT_APP_ID` を設定します。owner未設定ではtool callを拒否するため、
   bootstrap中にAPIが呼ばれることはありません。Site固有IDはSiteを作り直したら再設定します。
5. `get_site(include_mcp_connection: true)` の `has_mcp` とplugin IDを確認し、Sitesが
   provisionした既存App/pluginを使用します。新規接続は `plugin_management.suggest_plugins` で
   installation UIを出します。独自OAuthや `codex mcp add/login` は不要です。
6. authenticated discoveryが13ツールとschemaを返し、接続したclientから
   `get_stats_fields` が17分野を返すことを確認します。e-Stat readの確認は明示的な
   対象に限定し、dataset writeの実環境試験は別の許可済みfixtureでのみ行います。

deployment、authenticated discovery、client実呼出し、e-Stat実API結果は別の証拠です。
build成功やHTTP 200だけで接続・権限・実APIの受入済みとは扱いません。

## Contract and operational limits

- 13ツールのschema・default・annotations・JSON/CSV結果をPythonから保持します。
  e-Statへの `dataSetId` / `startPosition` / `statsDataId` などのcasingも維持します。
  HTTP bodyは1 MiBまで、JavaScriptで正確に表せないpaging整数は拒否します。
- `refDataset` のpagingは取得後にWorker側で適用します。catalog CSVは
  `json/getDataCatalog` の応答をローカル変換し、`MCP_GUIDANCE` とtimeout復旧を保持します。
- APIが `PARAMETER.APP_ID` 等にechoしたruntime secretは `[redacted]` に置換します。
  Pythonの既存応答に対する意図的な差分です。通信エラーにupstream URL、body、stackを載せません。
- `post_dataset` は登録・更新・削除を行う既存write toolです。自動retryや重複排除は追加しません。
  timeout / HTTP失敗後のwrite結果は不明の場合があるため、`get_dataset` で確認してから判断します。
- upstream timeoutは30秒です。大きい取得結果はSitesの128 MiB isolate制限を受けます。
  upstreamデータのstreaming、任意URL/path/shell forwarding、DB、独自OAuthは追加していません。

2026-10-10に照合した公式資料:
[MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)、
[MCP 2025-11-25互換transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)、
[MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)、
[公式TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)、
[e-Stat API 3.0](https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0)。
Sites runtime・manifest・identityはinstalled official Sites skillの
`references/site-mcp-server.md`、`identity-and-secrets.md`、`storage.md` と
`templates/worker-esm-starter/README.md` に従います。

## Cleanup

testsは自分で起動したMiniflare/workerdを `dispose()` で停止します。実Site、container、
DB、storage、plugin、tunnelを作りません。生成fixture・archive・bundleは
`.sites-generated/` と `dist/` のみに置きます。検証終了後に所有を確認し、今回のcheckout内の
生成物、`node_modules/`、`.venv/`、作業専用cacheだけを削除してください。
shared cache、元checkout、PR branch、source worktree、既存サービスは削除しません。
