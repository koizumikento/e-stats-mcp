# インストール/セットアップ
- `uv sync` : 依存関係をインストール（pyproject基準）。
- `export E_STAT_APP_ID=...` : 必須APIキー設定。

# 実行
- `uv run e-stats-mcp` : MCPサーバー起動（ローカル開発）。
- `uvx --from git+https://github.com/koizumikento/e-stats-mcp.git e-stats-mcp` : インストールなしで実行例。

# 品質チェック
- `uv run ruff check .` : Lint。
- `uv run mypy e_stats_mcp` : 型チェック。
- `uv run pytest` : テスト（現状tests空だが実行可能）。
- （必要なら）`uv run ruff format .` : フォーマット。

# よく使うユーティリティ（macOS/Darwin）
- `ls`, `cd`, `find . -name "pattern"` : ファイル確認。
- `rg "keyword"` : 高速grep。
- `git status` / `git diff` : 変更確認。