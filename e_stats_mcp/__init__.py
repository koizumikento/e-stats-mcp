"""e-Stat API MCP Server.

政府統計の総合窓口（e-Stat）APIにアクセスするためのMCPサーバー。
"""

from typing import TYPE_CHECKING

from e_stats_mcp.main import main, mcp

__version__ = "0.4.0"

if TYPE_CHECKING:
    from e_stats_mcp.cli import cli_main

__all__ = ["__version__", "main", "mcp", "cli_main"]


def __getattr__(name: str):
    """遅延インポート（typerをMCPモードで読み込まないため）."""
    if name == "cli_main":
        from e_stats_mcp.cli import cli_main

        return cli_main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

