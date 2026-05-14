"""データセット登録・参照ツール.

e-Stat APIのデータセット登録(postDataset)・参照(refDataset)を扱う。
"""

from typing import Any, cast
import xml.etree.ElementTree as ET

from e_stats_mcp.tools.stats import (
    _make_request,
    _raise_for_xml_error,
    _strip_namespace,
    _validate_positive_int,
)

POST_DATASET_RESERVED_CONDITION_KEYS = {
    "appId",
    "dataSetId",
    "dataSetName",
    "lang",
    "openSpecified",
    "processMode",
    "statsDataId",
}


async def post_dataset(
    dataset_name: str | None = None,
    stats_data_id: str | None = None,
    conditions: dict | None = None,
    data_set_id: str | None = None,
    open_specified: str | None = None,
    process_mode: str = "E",
) -> dict:
    """データセットを登録する.

    Args:
        dataset_name: データセット名
        stats_data_id: 統計表ID（登録・更新時に必須）
        conditions: 取得条件（cdCatXX, cdTime, cdArea などを辞書で指定）
        data_set_id: 更新・削除対象のデータセットID（削除時に必須）
        open_specified: 公開可否（e-Stat APIのopenSpecified）
        process_mode: 処理モード（E: 登録・更新、D: 削除）

    Returns:
        登録結果
    """
    _validate_post_dataset_args(
        process_mode=process_mode,
        stats_data_id=stats_data_id,
        data_set_id=data_set_id,
    )

    params: dict[str, Any] = {
        "processMode": process_mode,
    }
    if dataset_name:
        params["dataSetName"] = dataset_name
    if stats_data_id:
        params["statsDataId"] = stats_data_id
    if data_set_id:
        params["dataSetId"] = data_set_id
    if open_specified:
        params["openSpecified"] = open_specified
    if conditions:
        _validate_post_dataset_conditions(conditions)
        params.update(conditions)

    response = await _make_request(
        "postDataset",
        params,
        method="POST",
        format="xml",
        data=params,
    )
    return _parse_post_dataset_xml(cast(str, response))


def _validate_post_dataset_args(
    *,
    process_mode: str,
    stats_data_id: str | None,
    data_set_id: str | None,
) -> None:
    """postDatasetのモード別必須項目を検査する."""
    if process_mode not in {"E", "D"}:
        raise ValueError("process_modeは'E'または'D'を指定してください。")
    if process_mode == "E" and not stats_data_id:
        raise ValueError("process_mode='E'ではstats_data_idが必要です。")
    if process_mode == "D" and not data_set_id:
        raise ValueError("process_mode='D'ではdata_set_idが必要です。")


def _validate_post_dataset_conditions(conditions: dict[Any, Any]) -> None:
    """絞り込み条件がpostDatasetの制御パラメータを上書きしないようにする."""
    reserved_keys = POST_DATASET_RESERVED_CONDITION_KEYS.intersection(conditions)
    if reserved_keys:
        keys = ", ".join(sorted(reserved_keys))
        raise ValueError(f"conditionsに予約パラメータは指定できません: {keys}")


def _parse_post_dataset_xml(text: str) -> dict[str, Any]:
    """postDatasetのXMLレスポンスをMCPで扱いやすいdictに変換する."""
    _raise_for_xml_error(text)
    root = ET.fromstring(text)

    return {
        "result": _parse_result(_find_child(root, "RESULT")),
        "parameter": _parse_parameter(_find_child(root, "PARAMETER")),
        "dataset": _parse_regist_inf(_find_child(root, "REGIST_INF")),
    }


def _parse_result(element: ET.Element | None) -> dict[str, str]:
    if element is None:
        return {}
    return {
        "status": _child_text(element, "STATUS"),
        "error_message": _child_text(element, "ERROR_MSG"),
        "date": _child_text(element, "DATE"),
    }


def _parse_parameter(element: ET.Element | None) -> dict[str, Any]:
    if element is None:
        return {}

    parameter: dict[str, Any] = {}
    for child in element:
        tag = _strip_namespace(child.tag)
        if len(child):
            parameter[_to_snake_case(tag)] = _parse_nested_xml(child)
        else:
            parameter[_to_snake_case(tag)] = child.text or ""
    return parameter


def _parse_regist_inf(element: ET.Element | None) -> dict[str, Any]:
    if element is None:
        return {}

    dataset = {
        "mode": element.attrib.get("mode", ""),
        "dataset_id": _child_text(element, "DATASET_ID"),
        "stats_data_id": _child_text(element, "STATS_DATA_ID"),
        "public_state": _child_text(element, "PUBLIC_STATE"),
        "total_number": _child_text(element, "TOTAL_NUMBER"),
    }
    return {key: value for key, value in dataset.items() if value != ""}


def _parse_nested_xml(element: ET.Element) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for child in element:
        key = _to_snake_case(_strip_namespace(child.tag))
        nested[key] = _parse_nested_xml(child) if len(child) else child.text or ""
    return nested


def _child_text(element: ET.Element, tag: str) -> str:
    child = _find_child(element, tag)
    return child.text if child is not None and child.text is not None else ""


def _find_child(element: ET.Element, tag: str) -> ET.Element | None:
    """名前空間を無視して直下のXML子要素を探す."""
    for child in element:
        if _strip_namespace(child.tag) == tag:
            return child
    return None


def _to_snake_case(tag: str) -> str:
    return tag.lower()


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
        params["dataSetId"] = dataset_id
    if start_position is not None:
        params["startPosition"] = str(
            _validate_positive_int("start_position", start_position)
        )
    if limit is not None:
        params["limit"] = str(_validate_positive_int("limit", limit))

    response = await _make_request("json/refDataset", params)
    return cast(dict[str, Any], response)
