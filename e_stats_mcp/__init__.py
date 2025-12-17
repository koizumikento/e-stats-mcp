"""e-Stat API MCP Server.

政府統計の総合窓口（e-Stat）APIにアクセスするためのMCPサーバー。
"""

from e_stats_mcp.main import main, mcp
from e_stats_mcp.cli import cli_main

__all__ = ["main", "mcp", "cli_main"]

