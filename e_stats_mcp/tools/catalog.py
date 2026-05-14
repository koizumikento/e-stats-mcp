"""データカタログ情報取得ツール."""

import csv
from io import StringIO
from typing import Any, cast

from e_stats_mcp.tools.stats import _make_request, _validate_positive_int


async def get_data_catalog(
    search_word: str | None = None,
    stats_field: str | None = None,
    stats_code: str | None = None,
    gov_code: str | None = None,
    survey_years: str | None = None,
    open_years: str | None = None,
    stats_name_list: str | None = None,
    updated_date: str | None = None,
    start_position: int | None = None,
    limit: int | None = None,
) -> dict:
    """データカタログ情報を取得する.

    Args:
        search_word: 検索キーワード
        stats_field: 統計分野コード
        stats_code: 政府統計コード
        gov_code: 政府機関コード
        survey_years: 調査年
        open_years: 公開年
        stats_name_list: 調査・集計の種類
        updated_date: 更新日
        start_position: データ取得開始位置
        limit: 取得件数

    Returns:
        データカタログ情報
    """
    params = _build_data_catalog_params(
        search_word=search_word,
        stats_field=stats_field,
        stats_code=stats_code,
        gov_code=gov_code,
        survey_years=survey_years,
        open_years=open_years,
        stats_name_list=stats_name_list,
        updated_date=updated_date,
        start_position=start_position,
        limit=limit,
    )

    response = await _make_request("json/getDataCatalog", params)
    return cast(dict[str, Any], response)


def _build_data_catalog_params(
    *,
    search_word: str | None = None,
    stats_field: str | None = None,
    stats_code: str | None = None,
    gov_code: str | None = None,
    survey_years: str | None = None,
    open_years: str | None = None,
    stats_name_list: str | None = None,
    updated_date: str | None = None,
    start_position: int | None = None,
    limit: int | None = None,
) -> dict[str, str]:
    """getDataCatalog系の共通パラメータを組み立てる."""
    params: dict[str, str] = {}
    if search_word:
        params["searchWord"] = search_word
    if stats_field:
        params["statsField"] = stats_field
    if stats_code:
        params["statsCode"] = stats_code
    if gov_code:
        params["governmentCode"] = gov_code
    if survey_years:
        params["surveyYears"] = survey_years
    if open_years:
        params["openYears"] = open_years
    if stats_name_list:
        params["statsNameList"] = stats_name_list
    if updated_date:
        params["updatedDate"] = updated_date
    if start_position is not None:
        params["startPosition"] = str(
            _validate_positive_int("start_position", start_position)
        )
    if limit is not None:
        params["limit"] = str(_validate_positive_int("limit", limit))
    return params


async def get_data_catalog_csv(
    search_word: str | None = None,
    stats_field: str | None = None,
    stats_code: str | None = None,
    gov_code: str | None = None,
    survey_years: str | None = None,
    open_years: str | None = None,
    stats_name_list: str | None = None,
    updated_date: str | None = None,
    start_position: int | None = None,
    limit: int | None = None,
) -> str:
    """データカタログ情報をCSVで取得する.

    e-Stat API 3.0にはデータカタログのCSVエンドポイントがないため、
    JSON版getDataCatalogのデータカタログ行をMCP側でCSVへ変換する。
    """
    params = _build_data_catalog_params(
        search_word=search_word,
        stats_field=stats_field,
        stats_code=stats_code,
        gov_code=gov_code,
        survey_years=survey_years,
        open_years=open_years,
        stats_name_list=stats_name_list,
        updated_date=updated_date,
        start_position=start_position,
        limit=limit,
    )
    response = await _make_request("json/getDataCatalog", params)
    return _data_catalog_response_to_csv(cast(dict[str, Any], response))


def _data_catalog_response_to_csv(response: dict[str, Any]) -> str:
    """getDataCatalogのJSONレスポンスからDATA_CATALOG_INFをCSV化する."""
    catalog_info = (
        response.get("GET_DATA_CATALOG", {})
        .get("DATA_CATALOG_LIST_INF", {})
        .get("DATA_CATALOG_INF", [])
    )
    records = _ensure_list(catalog_info)
    flattened_records = [_flatten_record(record) for record in records]
    if not flattened_records:
        return ""

    fieldnames = sorted({key for record in flattened_records for key in record})
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(flattened_records)
    return output.getvalue()


def _ensure_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def _flatten_record(value: Any, prefix: str = "") -> dict[str, str]:
    """ネストしたdict/listをCSV列へ落とす."""
    if isinstance(value, dict):
        flattened: dict[str, str] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_record(child, child_prefix))
        return flattened
    if isinstance(value, list):
        return {
            prefix: ";".join(
                _stringify_flattened_value(item)
                for item in value
                if _stringify_flattened_value(item) != ""
            )
        }
    return {prefix: "" if value is None else str(value)}


def _stringify_flattened_value(value: Any) -> str:
    if isinstance(value, dict):
        return ";".join(
            f"{key}={child}" for key, child in _flatten_record(value).items()
        )
    if isinstance(value, list):
        return ";".join(_stringify_flattened_value(item) for item in value)
    return "" if value is None else str(value)
