# e-Stat MCP

政府統計の総合窓口（e-Stat）で統計表を探し、統計値や表の項目を取得できます。MCP、CLI、Pythonライブラリとして使えます。

[MCP登録](#mcpクライアントに登録する) · [CLI](#cliで使う) · [Pythonライブラリ](#pythonライブラリとして使う)

## できること

- 統計表情報の検索（JSON/CSV）
- 統計データの取得・一括取得（JSON/CSV）
- メタ情報の取得（JSON/CSV）
- データセットの登録・参照
- データカタログ情報の取得（JSON/CSV）
- キーワード検索

## データの出典

- e-Stat API: <https://www.e-stat.go.jp/api/>
- API仕様: <https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0>
- 利用規約: <https://www.e-stat.go.jp/terms-of-use>

出典：政府統計の総合窓口（e-Stat）（<https://www.e-stat.go.jp/>）

## インストール

```bash
uv tool install git+https://github.com/koizumikento/e-stats-mcp.git
```

リポジトリをクローンして使う場合は、次のコマンドを実行します。

```bash
git clone https://github.com/koizumikento/e-stats-mcp.git
cd e-stats-mcp
uv sync
```

## 設定

### アプリケーションID

e-Stat APIを使用するにはアプリケーションIDが必要です。

1. [e-Stat API](https://www.e-stat.go.jp/api/) にアクセス
2. ユーザー登録・ログイン
3. アプリケーションIDを取得

CLIとPythonを実行するシェルで環境変数を設定します。

```powershell
$env:E_STAT_APP_ID = "your-app-id"
```

macOSやLinuxでは `export E_STAT_APP_ID="your-app-id"` を使います。

## MCPクライアントに登録する

### Claude Desktop

OSに応じて、次のファイルに設定を追加します。

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**インストール済みのコマンドで起動する場合**

```json
{
  "mcpServers": {
    "e-stats-mcp": {
      "command": "e-stats-mcp",
      "env": {
        "E_STAT_APP_ID": "your-app-id"
      }
    }
  }
}
```

**GitHubから直接起動する場合**

```json
{
  "mcpServers": {
    "e-stats-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/koizumikento/e-stats-mcp.git",
        "e-stats-mcp"
      ],
      "env": {
        "E_STAT_APP_ID": "your-app-id"
      }
    }
  }
}
```

**クローン先から起動する場合**

```json
{
  "mcpServers": {
    "e-stats-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/e-stats-mcp",
        "e-stats-mcp"
      ],
      "env": {
        "E_STAT_APP_ID": "your-app-id"
      }
    }
  }
}
```

### Codex

CLIで登録する場合は、次のコマンドを実行します。アプリケーションIDは手元で差し替えてください。

```sh
codex mcp add e-stats-mcp --env "E_STAT_APP_ID=your-app-id" -- uvx --python 3.12 --from git+https://github.com/koizumikento/e-stats-mcp.git@master e-stats-mcp
codex mcp list
```

新しいセッションで `/mcp` を開くと接続を確認できます。手動で設定する場合は `~/.codex/config.toml` に追加します。 [OpenAI公式のMCP設定](https://learn.chatgpt.com/docs/extend/mcp)

**GitHubから起動する場合**

```toml
[mcp_servers.e-stats-mcp]
command = "uvx"
args = [
  "--from",
  "git+https://github.com/koizumikento/e-stats-mcp.git",
  "e-stats-mcp",
]
env = { E_STAT_APP_ID = "your-app-id" }
```

**クローン先から起動する場合**

```toml
[mcp_servers.e-stats-mcp]
command = "uv"
args = [
  "run",
  "--directory",
  "/path/to/e-stats-mcp",
  "e-stats-mcp",
]
env = { E_STAT_APP_ID = "your-app-id" }
```

### Cursor

プロジェクトのルートにある `.cursor/mcp.json` に設定を追加します。

```json
{
  "mcpServers": {
    "e-stats-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/koizumikento/e-stats-mcp.git",
        "e-stats-mcp"
      ],
      "env": {
        "E_STAT_APP_ID": "your-app-id"
      }
    }
  }
}
```

## ツール

### Sites Worker

Python library / CLI / stdioに加え、Sites内のWorkerとして全14ツールを実行できます。
別backend・tunnel・DBは不要です。ビルド、runtime secrets、所有者認可、配備・検証と
検証資源の片づけは [Sites手順](docs/sites.md) を参照してください。

### 統計表検索

- `get_stats_list` / `get_stats_list_csv` - 統計表情報を検索
- `search_stats_by_keyword` - キーワードで簡単検索

### メタ情報取得

- `get_meta_info` / `get_meta_info_csv` - 統計表のメタ情報を取得

### 統計データ取得

- `get_stats_data` / `get_stats_data_csv` - 統計データを取得
- `get_stats_data_bulk` - statsDatasSpec形式で複数ID/データセットを一括取得
- `get_stats_data_bulk_csv` - 同じ条件を使い、公式APIのCSV形式で一括取得

### データセット

- `post_dataset` - データセット登録（postDataset）
- `get_dataset` - データセット参照（refDataset）

e-Stat APIの `refDataset` では、一覧取得時に `limit` や `startPosition` を指定できません。
`get_dataset` で一覧を取得すると、MCPが `limit` と `start_position` を適用します。

### データカタログ

- `get_data_catalog` / `get_data_catalog_csv` - データカタログ情報を取得

データカタログの検索に時間がかかる場合は、先に `get_stats_list` で統計表を探してください。得られた `stats_code` などで条件を絞り、`get_data_catalog` を呼びます。

検索範囲が広すぎる場合やe-Stat APIが時間内に応答しない場合は、`MCP_GUIDANCE` または `structuredContent.error` に次に試せる呼び出しを返します。`get_data_catalog_csv` も検索範囲が広すぎる場合は、`csv` と `MCP_GUIDANCE` を含むJSONを返します。

### 分野コード

- `get_stats_fields` - 統計分野コード一覧（静的マッピング）

## CLIで使う

[アプリケーションID](#アプリケーションid)を設定してから実行します。通常の出力はJSONで、`--csv` を指定するとCSVを標準出力に返します。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/e-stats-mcp.git@master e-stats-mcp search 人口 --limit 5
uvx --python 3.12 --from git+https://github.com/koizumikento/e-stats-mcp.git@master e-stats-mcp data-bulk --ids "0003411001,0003411002" --limit 5 --csv
```

## Pythonライブラリとして使う

自分のPythonプロジェクト（`pyproject.toml` があるディレクトリ）で依存関係に追加します。[CLIで使う](#cliで使う)と同様に、実行するシェルで `E_STAT_APP_ID` を設定してください。

```sh
uv add "git+https://github.com/koizumikento/e-stats-mcp.git@master"
```

次のコードを `example.py` に保存し、同じディレクトリで `uv run python example.py` を実行します。

```python
import asyncio

from e_stats_mcp.tools import search_stats_by_keyword

print(asyncio.run(search_stats_by_keyword("人口", limit=5)))
```

## 使用例

### キーワードで統計を検索

```bash
Tool: search_stats_by_keyword
Arguments: {"keyword": "人口", "limit": 10}
```

### 統計表情報をCSVで取得

```bash
Tool: get_stats_list_csv
Arguments: {"search_word": "国勢調査", "survey_years": "2020", "limit": 5}
```

### 統計表情報を詳細検索

```bash
Tool: get_stats_list
Arguments: {"search_word": "国勢調査", "survey_years": "2020"}
```

### 統計データを取得

```bash
Tool: get_stats_data
Arguments: {"stats_data_id": "0003411001", "limit": 50}
```

### 統計データを一括取得

```bash
Tool: get_stats_data_bulk
Arguments: {
  "requests": [
    {"statsDataId": "0003411001", "limit": "100"},
    {"statsDataId": "0003411002", "limit": "100"}
  ]
}
```

`stats_data_ids` または `dataset_ids` でIDをまとめて指定できます。MCPは、これらの指定をe-Stat API用の `statsDatasSpec` に変換します。`limit` と `startPosition` はAPIが受け付ける文字列に変換します。

CSVが必要な場合は `get_stats_data_bulk_csv` に同じ引数を渡せます。CLIでは `e-stats-mcp data-bulk --ids 0003411001,0003411002 --csv` を使います。

### メタ情報を取得

```bash
Tool: get_meta_info
Arguments: {"stats_data_id": "0003411001"}
```

### データセットを登録

```bash
Tool: post_dataset
Arguments: {
  "dataset_name": "sample-dataset",
  "stats_data_id": "0003411001",
  "conditions": {"cdCat01": "000"}
}
```

`postDataset` はe-Stat API側の応答がXMLのみのため、このMCPではXMLをdictに変換して返します。
APIの業務エラーは通常データではなくツールエラーとして扱います。

### データカタログ情報をCSVで取得

```bash
Tool: get_data_catalog_csv
Arguments: {"search_word": "人口", "limit": 20}
```

e-Stat API 3.0にはデータカタログをCSVで取得する機能がありません。
MCPは `getDataCatalog` がJSONで返す `DATA_CATALOG_INF` をCSVに変換します。

### 統計分野コード一覧を取得

```bash
Tool: get_stats_fields
Arguments: {}
```

## 統計分野コード

| コード | 分野                       |
| ------ | -------------------------- |
| 01     | 国土・気象                 |
| 02     | 人口・世帯                 |
| 03     | 労働・賃金                 |
| 04     | 農林水産業                 |
| 05     | 鉱工業                     |
| 06     | 商業・サービス業           |
| 07     | 企業・家計・経済           |
| 08     | 住宅・土地・建設           |
| 09     | エネルギー・水             |
| 10     | 運輸・観光                 |
| 11     | 情報通信・科学技術         |
| 12     | 教育・文化・スポーツ・生活 |
| 13     | 行財政                     |
| 14     | 司法・安全・環境           |
| 15     | 社会保障・衛生             |
| 16     | 国際                       |
| 17     | その他                     |

## ライセンス

[MIT](LICENSE)
