# e-Stat MCP

政府統計の総合窓口（e-Stat）API MCP サーバー。

## Features

- 統計表情報の検索（JSON/CSV）
- 統計データの取得・一括取得（JSON/CSV）
- メタ情報の取得（JSON/CSV）
- データセットの登録・参照
- データカタログ情報の取得（JSON/CSV）
- キーワード検索

## Data Source

- e-Stat API: <https://www.e-stat.go.jp/api/>
- API仕様: <https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0>

## Installation

```bash
uv tool install git+https://github.com/koizumikento/e-stats-mcp.git
```

Or install locally:

```bash
git clone https://github.com/koizumikento/e-stats-mcp.git
cd e-stats-mcp
uv sync
```

## Configuration

### Application ID

e-Stat APIを使用するにはアプリケーションIDが必要です。

1. [e-Stat API](https://www.e-stat.go.jp/api/) にアクセス
2. ユーザー登録・ログイン
3. アプリケーションIDを取得

環境変数に設定:

```bash
export E_STAT_APP_ID="your-app-id"
```

## MCP Server Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

**Installed version:**

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

**Direct from GitHub:**

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

**Local development:**

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

### Cursor

Add to `.cursor/mcp.json` in your project root:

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

## Available Tools

### 統計表検索

- `get_stats_list` / `get_stats_list_csv` - 統計表情報を検索
- `search_stats_by_keyword` - キーワードで簡単検索

### メタ情報取得

- `get_meta_info` / `get_meta_info_csv` - 統計表のメタ情報を取得

### 統計データ取得

- `get_stats_data` / `get_stats_data_csv` - 統計データを取得
- `get_stats_data_bulk` - statsDatasSpec形式で複数ID/データセットを一括取得

### データセット

- `post_dataset` - データセット登録（postDataset）
- `get_dataset` - データセット参照（refDataset）

### データカタログ

- `get_data_catalog` / `get_data_catalog_csv` - データカタログ情報を取得

### 分野コード

- `get_stats_fields` - 統計分野コード一覧（静的マッピング）

## Examples

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

`stats_data_ids` / `dataset_ids` も後方互換用に利用できますが、e-Stat APIには内部で
`statsDatasSpec` JSON文字列として送信されます。`limit` / `startPosition` はMCP側で
e-Stat APIが受け付ける文字列形式に正規化されます。

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

e-Stat API 3.0にはデータカタログ取得のCSVエンドポイントがないため、MCP側で
JSON版 `getDataCatalog` の `DATA_CATALOG_INF` をCSVへ変換して返します。

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

## License

MIT
