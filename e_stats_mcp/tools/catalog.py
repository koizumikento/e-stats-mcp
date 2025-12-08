"""データカタログ情報取得ツール."""

from e_stats_mcp.tools.stats import _make_request


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
    params: dict = {}
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
    if start_position:
        params["startPosition"] = str(start_position)
    if limit:
        params["limit"] = str(limit)

    return await _make_request("json/getDataCatalog", params)


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
    """データカタログ情報をCSVで取得する."""
    params: dict = {}
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
    if start_position:
        params["startPosition"] = str(start_position)
    if limit:
        params["limit"] = str(limit)

    return await _make_request(
        "getSimpleDataCatalog",
        params,
        format="csv",
    )

