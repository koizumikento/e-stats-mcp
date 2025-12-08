"""統計データ関連のツール.

e-Stat APIを使用した統計データの検索・取得ツール。
"""

import os

import httpx

# e-Stat API設定
E_STAT_API_BASE = "https://api.e-stat.go.jp/rest/3.0/app"
API_KEY = os.environ.get("E_STAT_API_KEY", "")


async def _make_request(
    endpoint: str,
    params: dict | None = None,
) -> dict:
    """e-Stat APIへのリクエストを実行する.

    Args:
        endpoint: APIエンドポイント
        params: クエリパラメータ

    Returns:
        APIレスポンス（JSON）

    Raises:
        ValueError: APIキーが設定されていない場合
        httpx.HTTPError: API通信エラー
    """
    if not API_KEY:
        raise ValueError(
            "E_STAT_API_KEY環境変数が設定されていません。"
            "https://www.e-stat.go.jp/api/ からAPIキーを取得してください。"
        )

    url = f"{E_STAT_API_BASE}/{endpoint}"
    request_params = {"appId": API_KEY, **(params or {})}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=request_params, timeout=30.0)
        response.raise_for_status()
        return response.json()


async def get_stats_list(
    search_word: str | None = None,
    survey_years: str | None = None,
    stats_field: str | None = None,
    stats_code: str | None = None,
    limit: int = 10,
) -> dict:
    """統計表情報を検索する.

    Args:
        search_word: 検索キーワード（統計表名、調査名など）
        survey_years: 調査年（YYYY形式、範囲指定はYYYY-YYYY）
        stats_field: 統計分野コード（2桁）
        stats_code: 政府統計コード（5桁または8桁）
        limit: 取得件数（デフォルト10件、最大100件）

    Returns:
        統計表情報のリスト
    """
    params = {
        "lang": "J",
        "limit": str(min(limit, 100)),
    }

    if search_word:
        params["searchWord"] = search_word
    if survey_years:
        params["surveyYears"] = survey_years
    if stats_field:
        params["statsField"] = stats_field
    if stats_code:
        params["statsCode"] = stats_code

    return await _make_request("json/getStatsList", params)


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

    return await _make_request("json/getMetaInfo", params)


async def get_stats_data(
    stats_data_id: str,
    cdcat01: str | None = None,
    cdcat02: str | None = None,
    cdcat03: str | None = None,
    cdtime: str | None = None,
    cdarea: str | None = None,
    limit: int = 100,
) -> dict:
    """統計データを取得する.

    Args:
        stats_data_id: 統計表ID
        cdcat01: 分類事項01のコード（絞り込み用）
        cdcat02: 分類事項02のコード（絞り込み用）
        cdcat03: 分類事項03のコード（絞り込み用）
        cdtime: 時間軸コード（絞り込み用）
        cdarea: 地域コード（絞り込み用）
        limit: 取得件数（デフォルト100件）

    Returns:
        統計データ
    """
    params = {
        "lang": "J",
        "statsDataId": stats_data_id,
        "limit": str(limit),
    }

    if cdcat01:
        params["cdCat01"] = cdcat01
    if cdcat02:
        params["cdCat02"] = cdcat02
    if cdcat03:
        params["cdCat03"] = cdcat03
    if cdtime:
        params["cdTime"] = cdtime
    if cdarea:
        params["cdArea"] = cdarea

    return await _make_request("json/getStatsData", params)


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
