"""統計データ関連のツール.

e-Stat APIを使用した統計データの検索・取得ツール。
"""

import json
from typing import Any, cast
import xml.etree.ElementTree as ET

import httpx

from e_stats_mcp.settings import get_settings

# e-Stat API設定
E_STAT_API_BASE = "https://api.e-stat.go.jp/rest/3.0/app"
DEFAULT_TIMEOUT = 30.0
SUCCESS_STATUSES = {"0", "1", "2"}


class EStatAPIError(ValueError):
    """e-Stat APIの業務エラー."""

    def __init__(self, status: str, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"e-Stat API error {status}: {message}")


async def _make_request(
    endpoint: str,
    params: dict | None = None,
    *,
    method: str = "GET",
    format: str = "json",
    data: dict | None = None,
) -> dict[str, Any] | str:
    """e-Stat APIへのリクエストを実行する.

    Args:
        endpoint: APIエンドポイント（例: \"json/getStatsList\"）
        params: クエリパラメータ
        method: HTTPメソッド（GET/POST）
        format: レスポンス形式（\"json\" または \"csv\"）
        data: POST時のフォームデータ

    Returns:
        JSONの場合はdict、CSVの場合は文字列

    Raises:
        ValueError: APIキーが設定されていない場合
        httpx.HTTPError: API通信エラー
    """
    settings = get_settings()
    if not settings.E_STAT_APP_ID:
        raise ValueError(
            "E_STAT_APP_ID環境変数が設定されていません。"
            "https://www.e-stat.go.jp/api/ からアプリケーションIDを取得してください。"
        )

    url = f"{E_STAT_API_BASE}/{endpoint}"
    request_params = {"appId": settings.E_STAT_APP_ID, **(params or {})}
    http_method = method.upper()

    async with httpx.AsyncClient() as client:
        if http_method == "POST":
            request_data = {**request_params, **(data or {})}
            response = await client.post(
                url, data=request_data, timeout=DEFAULT_TIMEOUT
            )
        else:
            response = await client.get(
                url, params=request_params, timeout=DEFAULT_TIMEOUT
            )

        response.raise_for_status()
        if format == "csv":
            _raise_for_xml_error(response.text)
            return response.text
        if format == "xml":
            return response.text

        result = response.json()
        _raise_for_api_error(result)
        return result


def _raise_for_api_error(response: dict[str, Any]) -> None:
    """JSONレスポンス内のe-Stat業務エラーを検査する."""
    result = _find_result(response)
    if not result:
        return

    status = str(result.get("STATUS", ""))
    if status and status not in SUCCESS_STATUSES:
        message = str(result.get("ERROR_MSG") or "API request failed")
        raise EStatAPIError(status, message)


def _find_result(value: Any) -> dict[str, Any] | None:
    """ネストしたJSONレスポンスから最初のRESULTを探す."""
    if isinstance(value, dict):
        result = value.get("RESULT")
        if isinstance(result, dict):
            return result
        for child in value.values():
            found = _find_result(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_result(child)
            if found:
                return found
    return None


def _raise_for_xml_error(text: str) -> None:
    """XML本文内のe-Stat業務エラーを検査する."""
    xml_text = text.lstrip()
    if not xml_text.startswith("<"):
        return

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return

    status = _find_xml_text(root, "STATUS")
    if status and status not in SUCCESS_STATUSES:
        message = _find_xml_text(root, "ERROR_MSG") or "API request failed"
        raise EStatAPIError(status, message)


def _find_xml_text(root: ET.Element, tag: str) -> str | None:
    """名前空間を無視してXMLタグのテキストを探す."""
    for element in root.iter():
        if _strip_namespace(element.tag) == tag:
            return element.text or ""
    return None


def _strip_namespace(tag: str) -> str:
    """XMLタグ名から名前空間を除く."""
    return tag.rsplit("}", 1)[-1]


def _validate_positive_int(name: str, value: int) -> int:
    """e-Statの1始まり/正数パラメータを検査する."""
    if value < 1:
        raise ValueError(f"{name}は1以上を指定してください。")
    return value


async def get_stats_list(
    search_word: str | None = None,
    survey_years: str | None = None,
    stats_field: str | None = None,
    stats_code: str | None = None,
    gov_code: str | None = None,
    open_years: str | None = None,
    stats_name_list: str | None = None,
    start_position: int | None = None,
    updated_date: str | None = None,
    limit: int = 10,
) -> dict:
    """統計表情報を検索する.

    Args:
        search_word: 検索キーワード（統計表名、調査名など）
        survey_years: 調査年（YYYY形式、範囲指定はYYYY-YYYY）
        stats_field: 統計分野コード（2桁）
        stats_code: 政府統計コード（5桁または8桁）
        gov_code: 政府機関コード
        open_years: 公開年（YYYY形式、範囲指定はYYYY-YYYY）
        stats_name_list: 調査・集計の種類
        start_position: データ取得開始位置
        updated_date: 更新日（YYYY-MM-DD）
        limit: 取得件数（デフォルト10件、最大100件）

    Returns:
        統計表情報のリスト
    """
    params = _build_stats_list_params(
        search_word=search_word,
        survey_years=survey_years,
        stats_field=stats_field,
        stats_code=stats_code,
        gov_code=gov_code,
        open_years=open_years,
        stats_name_list=stats_name_list,
        start_position=start_position,
        updated_date=updated_date,
        limit=limit,
    )

    response = await _make_request("json/getStatsList", params)
    return cast(dict[str, Any], response)


def _build_stats_list_params(
    *,
    search_word: str | None = None,
    survey_years: str | None = None,
    stats_field: str | None = None,
    stats_code: str | None = None,
    gov_code: str | None = None,
    open_years: str | None = None,
    stats_name_list: str | None = None,
    start_position: int | None = None,
    updated_date: str | None = None,
    limit: int = 10,
) -> dict:
    """getStatsList系の共通パラメータを組み立てる."""
    params = {
        "lang": "J",
        "limit": str(min(_validate_positive_int("limit", limit), 100)),
    }

    if search_word:
        params["searchWord"] = search_word
    if survey_years:
        params["surveyYears"] = survey_years
    if stats_field:
        params["statsField"] = stats_field
    if stats_code:
        params["statsCode"] = stats_code
    if gov_code:
        params["governmentCode"] = gov_code
    if open_years:
        params["openYears"] = open_years
    if stats_name_list:
        params["statsNameList"] = stats_name_list
    if start_position is not None:
        params["startPosition"] = str(
            _validate_positive_int("start_position", start_position)
        )
    if updated_date:
        params["updatedDate"] = updated_date

    return params


async def get_meta_info(stats_data_id: str) -> dict:
    """統計表のメタ情報を取得する.

    Args:
        stats_data_id: 統計表ID

    Returns:
        メタ情報（分類事項、時間軸など）
    """
    params = {
        "lang": "J",
        "statsDataId": stats_data_id,
    }

    response = await _make_request("json/getMetaInfo", params)
    return cast(dict[str, Any], response)


async def get_stats_data(
    stats_data_id: str,
    cdcat01: str | None = None,
    cdcat02: str | None = None,
    cdcat03: str | None = None,
    lvcat01: str | None = None,
    lvcat02: str | None = None,
    lvcat03: str | None = None,
    lvcat04: str | None = None,
    lvcat05: str | None = None,
    lvcat06: str | None = None,
    lvcat07: str | None = None,
    lvcat08: str | None = None,
    lvcat09: str | None = None,
    lvcat10: str | None = None,
    lvcat11: str | None = None,
    lvcat12: str | None = None,
    lvcat13: str | None = None,
    lvcat14: str | None = None,
    lvcat15: str | None = None,
    cdtime: str | None = None,
    cdarea: str | None = None,
    start_position: int | None = None,
    section_header_flg: bool | None = None,
    cnt_get_flg: bool = False,
    limit: int = 100,
) -> dict:
    """統計データを取得する.

    Args:
        stats_data_id: 統計表ID
        cdcat01: 分類事項01のコード（絞り込み用）
        cdcat02: 分類事項02のコード（絞り込み用）
        cdcat03: 分類事項03のコード（絞り込み用）
        lvcat01-lvcat15: 分類事項の階層レベル（lvCatXX）
        cdtime: 時間軸コード（絞り込み用）
        cdarea: 地域コード（絞り込み用）
        start_position: データ取得開始位置
        section_header_flg: セクションヘッダ出力フラグ（Trueで出力、Falseで非出力）
        cnt_get_flg: 件数取得フラグ（Trueで有効）
        limit: 取得件数（デフォルト100件）

    Returns:
        統計データ
    """
    params = _build_stats_data_params(
        stats_data_id=stats_data_id,
        cdcat01=cdcat01,
        cdcat02=cdcat02,
        cdcat03=cdcat03,
        lvcat01=lvcat01,
        lvcat02=lvcat02,
        lvcat03=lvcat03,
        lvcat04=lvcat04,
        lvcat05=lvcat05,
        lvcat06=lvcat06,
        lvcat07=lvcat07,
        lvcat08=lvcat08,
        lvcat09=lvcat09,
        lvcat10=lvcat10,
        lvcat11=lvcat11,
        lvcat12=lvcat12,
        lvcat13=lvcat13,
        lvcat14=lvcat14,
        lvcat15=lvcat15,
        cdtime=cdtime,
        cdarea=cdarea,
        start_position=start_position,
        section_header_flg=section_header_flg,
        cnt_get_flg=cnt_get_flg,
        limit=limit,
    )

    response = await _make_request("json/getStatsData", params)
    return cast(dict[str, Any], response)


def _build_stats_data_params(
    *,
    stats_data_id: str,
    cdcat01: str | None = None,
    cdcat02: str | None = None,
    cdcat03: str | None = None,
    lvcat01: str | None = None,
    lvcat02: str | None = None,
    lvcat03: str | None = None,
    lvcat04: str | None = None,
    lvcat05: str | None = None,
    lvcat06: str | None = None,
    lvcat07: str | None = None,
    lvcat08: str | None = None,
    lvcat09: str | None = None,
    lvcat10: str | None = None,
    lvcat11: str | None = None,
    lvcat12: str | None = None,
    lvcat13: str | None = None,
    lvcat14: str | None = None,
    lvcat15: str | None = None,
    cdtime: str | None = None,
    cdarea: str | None = None,
    start_position: int | None = None,
    section_header_flg: bool | None = None,
    cnt_get_flg: bool = False,
    limit: int = 100,
) -> dict:
    """getStatsData系の共通パラメータを組み立てる."""
    params = {
        "lang": "J",
        "statsDataId": stats_data_id,
        "limit": str(_validate_positive_int("limit", limit)),
    }

    if cdcat01:
        params["cdCat01"] = cdcat01
    if cdcat02:
        params["cdCat02"] = cdcat02
    if cdcat03:
        params["cdCat03"] = cdcat03
    lv_params = [
        lvcat01,
        lvcat02,
        lvcat03,
        lvcat04,
        lvcat05,
        lvcat06,
        lvcat07,
        lvcat08,
        lvcat09,
        lvcat10,
        lvcat11,
        lvcat12,
        lvcat13,
        lvcat14,
        lvcat15,
    ]
    for idx, value in enumerate(lv_params, start=1):
        if value:
            params[f"lvCat{idx:02d}"] = value
    if cdtime:
        params["cdTime"] = cdtime
    if cdarea:
        params["cdArea"] = cdarea
    if start_position is not None:
        params["startPosition"] = str(
            _validate_positive_int("start_position", start_position)
        )
    if section_header_flg is not None:
        params["sectionHeaderFlg"] = "1" if section_header_flg else "2"
    if cnt_get_flg:
        params["cntGetFlg"] = "Y"

    return params


async def search_stats_by_keyword(keyword: str, limit: int = 20) -> dict:
    """キーワードで統計情報を検索する.

    より簡単に統計表を検索するためのヘルパーツール。

    Args:
        keyword: 検索キーワード（例: "人口", "GDP", "雇用"）
        limit: 取得件数（デフォルト20件）

    Returns:
        検索結果のリスト
    """
    return await get_stats_list(search_word=keyword, limit=limit)


async def get_stats_list_csv(
    search_word: str | None = None,
    survey_years: str | None = None,
    stats_field: str | None = None,
    stats_code: str | None = None,
    gov_code: str | None = None,
    open_years: str | None = None,
    stats_name_list: str | None = None,
    start_position: int | None = None,
    updated_date: str | None = None,
    limit: int = 10,
) -> str:
    """統計表情報をCSVで取得する."""
    params = _build_stats_list_params(
        search_word=search_word,
        survey_years=survey_years,
        stats_field=stats_field,
        stats_code=stats_code,
        gov_code=gov_code,
        open_years=open_years,
        stats_name_list=stats_name_list,
        start_position=start_position,
        updated_date=updated_date,
        limit=limit,
    )
    response = await _make_request(
        "getSimpleStatsList",
        params,
        format="csv",
    )
    return cast(str, response)


async def get_meta_info_csv(stats_data_id: str) -> str:
    """統計表のメタ情報をCSVで取得する."""
    params = {
        "lang": "J",
        "statsDataId": stats_data_id,
    }
    response = await _make_request(
        "getSimpleMetaInfo",
        params,
        format="csv",
    )
    return cast(str, response)


async def get_stats_data_csv(
    stats_data_id: str,
    cdcat01: str | None = None,
    cdcat02: str | None = None,
    cdcat03: str | None = None,
    lvcat01: str | None = None,
    lvcat02: str | None = None,
    lvcat03: str | None = None,
    lvcat04: str | None = None,
    lvcat05: str | None = None,
    lvcat06: str | None = None,
    lvcat07: str | None = None,
    lvcat08: str | None = None,
    lvcat09: str | None = None,
    lvcat10: str | None = None,
    lvcat11: str | None = None,
    lvcat12: str | None = None,
    lvcat13: str | None = None,
    lvcat14: str | None = None,
    lvcat15: str | None = None,
    cdtime: str | None = None,
    cdarea: str | None = None,
    start_position: int | None = None,
    section_header_flg: bool | None = None,
    cnt_get_flg: bool = False,
    limit: int = 100,
) -> str:
    """統計データをCSVで取得する."""
    params = _build_stats_data_params(
        stats_data_id=stats_data_id,
        cdcat01=cdcat01,
        cdcat02=cdcat02,
        cdcat03=cdcat03,
        lvcat01=lvcat01,
        lvcat02=lvcat02,
        lvcat03=lvcat03,
        lvcat04=lvcat04,
        lvcat05=lvcat05,
        lvcat06=lvcat06,
        lvcat07=lvcat07,
        lvcat08=lvcat08,
        lvcat09=lvcat09,
        lvcat10=lvcat10,
        lvcat11=lvcat11,
        lvcat12=lvcat12,
        lvcat13=lvcat13,
        lvcat14=lvcat14,
        lvcat15=lvcat15,
        cdtime=cdtime,
        cdarea=cdarea,
        start_position=start_position,
        section_header_flg=section_header_flg,
        cnt_get_flg=cnt_get_flg,
        limit=limit,
    )
    response = await _make_request(
        "getSimpleStatsData",
        params,
        format="csv",
    )
    return cast(str, response)


async def get_stats_data_bulk(
    requests: list[dict[str, Any]] | None = None,
    stats_data_ids: list[str] | None = None,
    dataset_ids: list[str] | None = None,
    start_position: int | None = None,
    limit: int | None = None,
) -> dict:
    """複数の統計表ID/データセットIDから統計データを一括取得する.

    Args:
        requests: statsDatasSpecに入れる取得条件のリスト
        stats_data_ids: 後方互換用の統計表IDリスト
        dataset_ids: 後方互換用のデータセットIDリスト
        start_position: 後方互換用のデータ取得開始位置
        limit: 後方互換用の取得件数
    """
    stats_datas_spec = (
        _validate_bulk_requests(requests)
        if requests is not None
        else _build_bulk_requests(
            stats_data_ids=stats_data_ids,
            dataset_ids=dataset_ids,
            start_position=start_position,
            limit=limit,
        )
    )
    if not stats_datas_spec:
        raise ValueError("requests、stats_data_ids、dataset_idsのいずれかを指定してください。")

    params: dict[str, str] = {"lang": "J"}
    data = {
        "statsDatasSpec": json.dumps(stats_datas_spec, ensure_ascii=False),
    }

    response = await _make_request(
        "json/getStatsDatas",
        params,
        method="POST",
        data=data,
    )
    return cast(dict[str, Any], response)


def _validate_bulk_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """statsDatasSpec用リクエスト配列の最低限の形を検査する."""
    if not isinstance(requests, list):
        raise ValueError("requestsは取得条件dictのリストで指定してください。")
    for index, request in enumerate(requests, start=1):
        if not isinstance(request, dict):
            raise ValueError(f"requests[{index}]はdictで指定してください。")
        if not (request.get("statsDataId") or request.get("dataSetId")):
            raise ValueError(
                f"requests[{index}]にはstatsDataIdまたはdataSetIdが必要です。"
            )
    return requests


def _build_bulk_requests(
    *,
    stats_data_ids: list[str] | None = None,
    dataset_ids: list[str] | None = None,
    start_position: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """旧形式の入力からstatsDatasSpec用リクエストを作る."""
    requests: list[dict[str, Any]] = []
    common: dict[str, Any] = {}
    if start_position is not None:
        common["startPosition"] = _validate_positive_int(
            "start_position", start_position
        )
    if limit is not None:
        common["limit"] = _validate_positive_int("limit", limit)

    for stats_data_id in stats_data_ids or []:
        requests.append({"statsDataId": stats_data_id, **common})
    for dataset_id in dataset_ids or []:
        requests.append({"dataSetId": dataset_id, **common})

    return requests
