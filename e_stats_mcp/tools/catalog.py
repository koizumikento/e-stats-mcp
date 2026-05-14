"""データカタログ情報取得ツール."""

import csv
from io import StringIO
from typing import Any, cast

import httpx

from e_stats_mcp.tools.stats import _make_request, _validate_positive_int

BROAD_CATALOG_MATCH_THRESHOLD = 1000
CATALOG_GUIDANCE_KEY = "MCP_GUIDANCE"


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
) -> dict[str, Any]:
    """データカタログ情報を取得する.

    広い探索にはget_stats_listを使い、stats_code等で候補を絞ってから
    get_data_catalogを呼ぶと安定しやすい。

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

    try:
        response = await _make_request("json/getDataCatalog", params)
    except httpx.TimeoutException:
        return _build_data_catalog_recovery_result(
            code="UPSTREAM_TIMEOUT_QUERY_TOO_BROAD",
            search_word=search_word,
            matched_count_hint=None,
        )

    result = cast(dict[str, Any], response)
    return _add_broad_catalog_guidance(result, params)


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
) -> str | dict[str, Any]:
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
    try:
        response = await _make_request("json/getDataCatalog", params)
    except httpx.TimeoutException:
        return _build_data_catalog_recovery_result(
            code="UPSTREAM_TIMEOUT_QUERY_TOO_BROAD",
            search_word=search_word,
            matched_count_hint=None,
        )
    result = cast(dict[str, Any], response)
    guidance = _get_broad_catalog_guidance(result, params)
    csv_text = _data_catalog_response_to_csv(result)
    if guidance is None:
        return csv_text
    return {
        "csv": csv_text,
        CATALOG_GUIDANCE_KEY: guidance,
    }


def _add_broad_catalog_guidance(
    response: dict[str, Any],
    params: dict[str, str],
) -> dict[str, Any]:
    """広すぎるデータカタログ検索に次アクションのヒントを追加する."""
    guidance = _get_broad_catalog_guidance(response, params)
    if guidance is None:
        return response

    response[CATALOG_GUIDANCE_KEY] = guidance
    return response


def _get_broad_catalog_guidance(
    response: dict[str, Any],
    params: dict[str, str],
) -> dict[str, Any] | None:
    matched_count = _get_data_catalog_matched_count(response)
    if matched_count is None or matched_count < BROAD_CATALOG_MATCH_THRESHOLD:
        return None
    if not _is_broad_catalog_search(params):
        return None

    return _build_data_catalog_recovery_error(
        code="DATA_CATALOG_QUERY_TOO_BROAD",
        search_word=params.get("searchWord"),
        matched_count_hint=matched_count,
    )


def _is_broad_catalog_search(params: dict[str, str]) -> bool:
    narrowing_keys = {
        "statsCode",
        "statsField",
        "governmentCode",
        "surveyYears",
        "openYears",
        "statsNameList",
        "updatedDate",
    }
    return bool(params.get("searchWord")) and not any(
        key in params for key in narrowing_keys
    )


def _get_data_catalog_matched_count(response: dict[str, Any]) -> int | None:
    number = (
        response.get("GET_DATA_CATALOG", {})
        .get("DATA_CATALOG_LIST_INF", {})
        .get("NUMBER")
    )
    try:
        return int(number)
    except (TypeError, ValueError):
        return None


def _build_data_catalog_recovery_result(
    *,
    code: str,
    search_word: str | None,
    matched_count_hint: int | None,
) -> dict[str, Any]:
    error = _build_data_catalog_recovery_error(
        code=code,
        search_word=search_word,
        matched_count_hint=matched_count_hint,
    )
    return {
        "isError": True,
        "structuredContent": {"error": error},
        "content": [
            {
                "type": "text",
                "text": "Data catalog query is too broad. Try get_stats_list first, then retry get_data_catalog with stats_code or another narrowing parameter.",
            }
        ],
    }


def _build_data_catalog_recovery_error(
    *,
    code: str,
    search_word: str | None,
    matched_count_hint: int | None,
) -> dict[str, Any]:
    query = search_word or ""
    suggested_next_calls: list[dict[str, Any]] = []
    if query:
        suggested_next_calls.append(
            {
                "tool": "get_stats_list",
                "arguments": {"search_word": query, "limit": 10},
                "reason": "統計表候補を先に探索し、stats_codeを特定する",
            }
        )
    suggested_next_calls.append(
        {
            "tool": "get_data_catalog",
            "arguments": {"stats_code": "00200524", "limit": 1},
            "reason": "stats_code等で対象統計を絞ってデータカタログを取得する",
        }
    )

    return {
        "code": code,
        "message": "e-Stat data catalog search timed out or matched too many results. Narrow the query before retrying.",
        "retryable": True,
        "matched_count_hint": matched_count_hint,
        "suggested_next_calls": suggested_next_calls,
    }


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
