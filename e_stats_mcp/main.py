"""e-Stat API MCP Server.

政府統計の総合窓口（e-Stat）APIにアクセスするためのMCPサーバー。
e-Stat API: https://www.e-stat.go.jp/api/
"""

from fastmcp import FastMCP

from e_stats_mcp.tools import (
    get_meta_info,
    get_stats_data,
    get_stats_list,
    search_stats_by_keyword,
)

# MCPサーバー初期化
mcp = FastMCP(
    "e-stats-mcp",
    instructions="""
    e-Stat（政府統計の総合窓口）APIにアクセスするためのMCPサーバーです。
    
    主な機能:
    - 統計表情報の検索・取得
    - 統計データの取得
    - メタ情報の取得
    
    使用にはe-Stat APIキー（E_STAT_API_KEY環境変数）が必要です。
    APIキーは https://www.e-stat.go.jp/api/ から取得できます。
    """,
)

# ツールを登録
mcp.tool()(get_stats_list)
mcp.tool()(get_meta_info)
mcp.tool()(get_stats_data)
mcp.tool()(search_stats_by_keyword)


def main() -> None:
    """MCPサーバーを起動する."""
    mcp.run()


if __name__ == "__main__":
    main()
