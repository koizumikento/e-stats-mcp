# e-Stat MCP

政府統計の総合窓口（e-Stat）API MCP サーバー。

## Features

- 統計表情報の検索
- 統計データの取得
- メタ情報の取得
- キーワード検索

## Data Source

- e-Stat API: https://www.e-stat.go.jp/api/

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

### API Key

e-Stat APIを使用するにはAPIキーが必要です。

1. [e-Stat API](https://www.e-stat.go.jp/api/) にアクセス
2. ユーザー登録・ログイン
3. アプリケーションIDを取得

環境変数に設定:

```bash
export E_STAT_API_KEY="your-api-key"
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
        "E_STAT_API_KEY": "your-api-key"
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
        "E_STAT_API_KEY": "your-api-key"
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
        "E_STAT_API_KEY": "your-api-key"
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
        "E_STAT_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Available Tools

### 統計表検索

- `get_stats_list` - 統計表情報を検索
- `search_stats_by_keyword` - キーワードで簡単検索

### データ取得

- `get_stats_data` - 統計データを取得
- `get_meta_info` - 統計表のメタ情報を取得

## Examples

### キーワードで統計を検索

```bash
Tool: search_stats_by_keyword
Arguments: {"keyword": "人口", "limit": 10}
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

### メタ情報を取得

```bash
Tool: get_meta_info
Arguments: {"stats_data_id": "0003411001"}
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
