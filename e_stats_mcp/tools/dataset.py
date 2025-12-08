"""データセット登録・参照ツール.

e-Stat APIのデータセット登録(postDataset)・参照(refDataset)を扱う。
"""

from typing import Any, cast

from e_stats_mcp.tools.stats import _make_request


async def post_dataset(
    dataset_name: str,
    stats_data_id: str,
    conditions: dict | None = None,
    description: str | None = None,
) -> dict:
    """データセットを登録する.

    Args:
        dataset_name: データセット名
        stats_data_id: 統計表ID
        conditions: 取得条件（cdCatXX, cdTime, cdArea などを辞書で指定）
        description: 説明文

    Returns:
        登録結果
    """
    params = {
        "datasetName": dataset_name,
        "statsDataId": stats_data_id,
    }
    if description:
        params["description"] = description
    if conditions:
        params.update(conditions)

    response = await _make_request(
        "postDataset",
        params,
        method="POST",
        data=params,
    )
    return cast(dict[str, Any], response)


async def get_dataset(
    dataset_id: str | None = None,
    start_position: int | None = None,
    limit: int | None = None,
) -> dict:
    """データセットを参照する.

    Args:
        dataset_id: 取得対象のデータセットID（省略時は利用可能一覧）
        start_position: データ取得開始位置
        limit: 取得件数

    Returns:
        データセット情報
    """
    params: dict = {}
    if dataset_id:
        params["datasetId"] = dataset_id
    if start_position:
        params["startPosition"] = str(start_position)
    if limit:
        params["limit"] = str(limit)

    response = await _make_request("json/refDataset", params)
    return cast(dict[str, Any], response)

