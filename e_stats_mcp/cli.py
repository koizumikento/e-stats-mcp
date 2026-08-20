"""e-Stat API CLI.

コマンドラインからe-Stat APIにアクセスするためのCLIツール。
"""

import asyncio
import json
from typing import Annotated, Any

import typer

from e_stats_mcp.tools import (
    get_data_catalog,
    get_data_catalog_csv,
    get_dataset,
    get_meta_info,
    get_meta_info_csv,
    get_stats_data,
    get_stats_data_bulk,
    get_stats_data_csv,
    get_stats_fields,
    get_stats_list,
    get_stats_list_csv,
    post_dataset,
    search_stats_by_keyword,
)

app = typer.Typer(
    name="e-stats",
    help="e-Stat（政府統計の総合窓口）APIにアクセスするためのCLIツール",
    no_args_is_help=True,
)


def _print_json(data: dict[str, Any] | list[Any]) -> None:
    """JSON形式で出力する."""
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _print_csv(data: str) -> None:
    """CSV形式で出力する."""
    typer.echo(data)


# --- 統計表検索コマンド ---


@app.command("search")
def search_command(
    keyword: Annotated[
        str, typer.Argument(help="検索キーワード（例: 人口, GDP, 雇用）")
    ],
    limit: Annotated[int, typer.Option("--limit", "-l", help="取得件数")] = 20,
) -> None:
    """キーワードで統計表を検索する."""
    result = asyncio.run(search_stats_by_keyword(keyword=keyword, limit=limit))
    _print_json(result)


@app.command("list")
def stats_list_command(
    search_word: Annotated[
        str | None, typer.Option("--search", "-s", help="検索キーワード")
    ] = None,
    survey_years: Annotated[
        str | None, typer.Option("--year", "-y", help="調査年（YYYY形式）")
    ] = None,
    stats_field: Annotated[
        str | None, typer.Option("--field", "-f", help="統計分野コード（2桁）")
    ] = None,
    stats_code: Annotated[
        str | None, typer.Option("--code", "-c", help="政府統計コード")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="取得件数")] = 10,
    csv: Annotated[bool, typer.Option("--csv", help="CSV形式で出力")] = False,
) -> None:
    """統計表情報を検索する."""
    if csv:
        csv_result = asyncio.run(
            get_stats_list_csv(
                search_word=search_word,
                survey_years=survey_years,
                stats_field=stats_field,
                stats_code=stats_code,
                limit=limit,
            )
        )
        _print_csv(csv_result)
    else:
        json_result = asyncio.run(
            get_stats_list(
                search_word=search_word,
                survey_years=survey_years,
                stats_field=stats_field,
                stats_code=stats_code,
                limit=limit,
            )
        )
        _print_json(json_result)


# --- メタ情報コマンド ---


@app.command("meta")
def meta_info_command(
    stats_data_id: Annotated[str, typer.Argument(help="統計表ID")],
    csv: Annotated[bool, typer.Option("--csv", help="CSV形式で出力")] = False,
) -> None:
    """統計表のメタ情報を取得する."""
    if csv:
        csv_result = asyncio.run(get_meta_info_csv(stats_data_id=stats_data_id))
        _print_csv(csv_result)
    else:
        json_result = asyncio.run(get_meta_info(stats_data_id=stats_data_id))
        _print_json(json_result)


# --- 統計データ取得コマンド ---


@app.command("data")
def stats_data_command(
    stats_data_id: Annotated[str, typer.Argument(help="統計表ID")],
    cdcat01: Annotated[
        str | None, typer.Option("--cat01", help="分類事項01のコード")
    ] = None,
    cdcat02: Annotated[
        str | None, typer.Option("--cat02", help="分類事項02のコード")
    ] = None,
    cdcat03: Annotated[
        str | None, typer.Option("--cat03", help="分類事項03のコード")
    ] = None,
    cdtime: Annotated[
        str | None, typer.Option("--time", "-t", help="時間軸コード")
    ] = None,
    cdarea: Annotated[
        str | None, typer.Option("--area", "-a", help="地域コード")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="取得件数")] = 100,
    csv: Annotated[bool, typer.Option("--csv", help="CSV形式で出力")] = False,
) -> None:
    """統計データを取得する."""
    if csv:
        csv_result = asyncio.run(
            get_stats_data_csv(
                stats_data_id=stats_data_id,
                cdcat01=cdcat01,
                cdcat02=cdcat02,
                cdcat03=cdcat03,
                cdtime=cdtime,
                cdarea=cdarea,
                limit=limit,
            )
        )
        _print_csv(csv_result)
    else:
        json_result = asyncio.run(
            get_stats_data(
                stats_data_id=stats_data_id,
                cdcat01=cdcat01,
                cdcat02=cdcat02,
                cdcat03=cdcat03,
                cdtime=cdtime,
                cdarea=cdarea,
                limit=limit,
            )
        )
        _print_json(json_result)


@app.command("data-bulk")
def stats_data_bulk_command(
    request_json: Annotated[
        str | None,
        typer.Option(
            "--request-json",
            help="statsDatasSpec用の取得条件リストJSON。--ids/--datasetsより優先",
        ),
    ] = None,
    stats_data_ids: Annotated[
        str | None,
        typer.Option("--ids", "-i", help="統計表IDリスト（カンマ区切り）"),
    ] = None,
    dataset_ids: Annotated[
        str | None,
        typer.Option("--datasets", "-d", help="データセットIDリスト（カンマ区切り）"),
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="取得件数")
    ] = None,
) -> None:
    """複数の統計表/データセットから統計データを一括取得する."""
    requests = json.loads(request_json) if request_json else None
    ids_list = stats_data_ids.split(",") if stats_data_ids else None
    datasets_list = dataset_ids.split(",") if dataset_ids else None
    result = asyncio.run(
        get_stats_data_bulk(
            requests=requests,
            stats_data_ids=ids_list,
            dataset_ids=datasets_list,
            limit=limit,
        )
    )
    _print_json(result)


# --- データセットコマンド ---


@app.command("dataset-create")
def post_dataset_command(
    name: Annotated[str, typer.Option("--name", "-n", help="データセット名")],
    stats_data_id: Annotated[str, typer.Option("--id", "-i", help="統計表ID")],
    conditions_json: Annotated[
        str | None,
        typer.Option("--conditions-json", help="絞り込み条件のJSON"),
    ] = None,
) -> None:
    """データセットを登録する."""
    conditions = json.loads(conditions_json) if conditions_json else None
    result = asyncio.run(
        post_dataset(
            dataset_name=name,
            stats_data_id=stats_data_id,
            conditions=conditions,
        )
    )
    _print_json(result)


@app.command("dataset")
def get_dataset_command(
    dataset_id: Annotated[
        str | None, typer.Argument(help="データセットID（省略時は一覧取得）")
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="取得件数")
    ] = None,
) -> None:
    """データセットを参照する."""
    result = asyncio.run(get_dataset(dataset_id=dataset_id, limit=limit))
    _print_json(result)


# --- データカタログコマンド ---


@app.command("catalog")
def data_catalog_command(
    search_word: Annotated[
        str | None, typer.Option("--search", "-s", help="検索キーワード")
    ] = None,
    stats_field: Annotated[
        str | None, typer.Option("--field", "-f", help="統計分野コード")
    ] = None,
    stats_code: Annotated[
        str | None, typer.Option("--code", "-c", help="政府統計コード")
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="取得件数")
    ] = None,
    csv: Annotated[bool, typer.Option("--csv", help="CSV形式で出力")] = False,
) -> None:
    """データカタログ情報を取得する."""
    if csv:
        csv_result = asyncio.run(
            get_data_catalog_csv(
                search_word=search_word,
                stats_field=stats_field,
                stats_code=stats_code,
                limit=limit,
            )
        )
        if isinstance(csv_result, str):
            _print_csv(csv_result)
        else:
            _print_json(csv_result)
    else:
        json_result = asyncio.run(
            get_data_catalog(
                search_word=search_word,
                stats_field=stats_field,
                stats_code=stats_code,
                limit=limit,
            )
        )
        _print_json(json_result)


# --- 統計分野コードコマンド ---


@app.command("fields")
def stats_fields_command() -> None:
    """統計分野コード一覧を取得する."""
    result = asyncio.run(get_stats_fields())
    _print_json(result)


def cli_main() -> None:
    """CLIエントリポイント."""
    app()
