"""e-Stat API MCP Server.

政府統計の総合窓口（e-Stat）APIにアクセスするためのMCPサーバー。
e-Stat API: https://www.e-stat.go.jp/api/
"""

import sys

from fastmcp import FastMCP

from e_stats_mcp.tools import (
    get_data_catalog,
    get_data_catalog_csv,
    get_dataset,
    get_meta_info,
    get_meta_info_csv,
    get_stats_fields,
    get_stats_data,
    get_stats_data_bulk,
    get_stats_data_csv,
    get_stats_list,
    get_stats_list_csv,
    post_dataset,
    search_stats_by_keyword,
)

# MCPサーバー初期化
mcp = FastMCP(
    "e-stats-mcp",
    instructions="""
    e-Stat（政府統計の総合窓口）APIにアクセスするためのMCPサーバーです。

    主な機能 (JSON/CSV 両対応):
    - 統計表情報の検索・取得
    - メタ情報の取得
    - 統計データの取得・一括取得
    - データセットの登録・参照
    - データカタログ情報の取得

    使用にはe-Stat APIキー（E_STAT_API_KEY環境変数）が必要です。
    APIキーは https://www.e-stat.go.jp/api/ から取得できます。
    """,
)

# ツールを登録
mcp.tool()(get_stats_list)
mcp.tool()(get_stats_list_csv)
mcp.tool()(get_meta_info)
mcp.tool()(get_meta_info_csv)
mcp.tool()(get_stats_data)
mcp.tool()(get_stats_data_csv)
mcp.tool()(get_stats_data_bulk)
mcp.tool()(search_stats_by_keyword)
mcp.tool()(post_dataset)
mcp.tool()(get_dataset)
mcp.tool()(get_data_catalog)
mcp.tool()(get_data_catalog_csv)
mcp.tool()(get_stats_fields)


def main() -> None:
    """エントリポイント.

    引数なし、または --mcp の場合はMCPサーバーを起動。
    それ以外の引数がある場合はCLIモードを起動。
    """
    # 引数がない、または --mcp が指定された場合はMCPサーバーを起動
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == "--mcp"):
        mcp.run()
    else:
        # CLIモードを起動
        from e_stats_mcp.cli import cli_main

        cli_main()


if __name__ == "__main__":
    main()
