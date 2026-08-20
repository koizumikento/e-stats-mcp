import importlib
import json
from typing import Any, Self

import httpx
import pytest

from e_stats_mcp.tools import catalog, dataset, stats

server_main = importlib.import_module("e_stats_mcp.main")


class DummyResponse:
    def __init__(self, json_data: dict[str, Any] | None = None, text: str = ""):
        self._json_data = json_data or {}
        self.text = text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._json_data


class DummyClient:
    def __init__(self, response: DummyResponse):
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any] | None, Any, Any]] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def get(self, url: str, params=None, timeout=None):
        self.calls.append(("GET", url, params, None, timeout))
        return self.response

    async def post(self, url: str, params=None, data=None, timeout=None):
        self.calls.append(("POST", url, params, data, timeout))
        return self.response


def test_build_stats_list_params_clamps_limit_and_converts(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    params = stats._build_stats_list_params(
        search_word="人口",
        survey_years="2020-2021",
        stats_field="02",
        stats_code="12345",
        gov_code="00100",
        open_years="2020",
        stats_name_list="sample",
        start_position=5,
        updated_date="2024-01-01",
        limit=150,
    )
    assert params["limit"] == "100"
    assert params["searchWord"] == "人口"
    assert params["startPosition"] == "5"
    assert params["statsField"] == "02"
    assert params["statsCode"] == "12345"
    assert params["governmentCode"] == "00100"
    assert params["openYears"] == "2020"
    assert params["statsNameList"] == "sample"
    assert params["updatedDate"] == "2024-01-01"


def test_build_stats_list_params_rejects_invalid_paging(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    with pytest.raises(ValueError, match="start_position"):
        stats._build_stats_list_params(start_position=0)


def test_build_stats_data_params_builds_lv_and_flags(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    params = stats._build_stats_data_params(
        stats_data_id="0001",
        cdcat01="A",
        lvcat01="X",
        lvcat03="Z",
        cdtime="202001",
        cdarea="13000",
        start_position=2,
        section_header_flg=True,
        cnt_get_flg=False,
        limit=50,
    )
    assert params["statsDataId"] == "0001"
    assert params["cdCat01"] == "A"
    assert params["lvCat01"] == "X"
    assert params["lvCat03"] == "Z"
    assert params["cdTime"] == "202001"
    assert params["cdArea"] == "13000"
    assert params["startPosition"] == "2"
    assert params["sectionHeaderFlg"] == "1"
    assert "cntGetFlg" not in params
    assert params["limit"] == "50"


def test_build_stats_data_params_uses_estat_flag_values(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    params = stats._build_stats_data_params(
        stats_data_id="0001",
        section_header_flg=False,
        cnt_get_flg=True,
    )
    assert params["sectionHeaderFlg"] == "2"
    assert params["cntGetFlg"] == "Y"


@pytest.mark.asyncio
async def test_make_request_returns_json(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(json_data={"ok": True})
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await stats._make_request("json/test", {"x": "1"})
    assert result == {"ok": True}

    assert len(client.calls) == 1
    method, url, params, data, timeout = client.calls[0]
    assert method == "GET"
    assert url == f"{stats.E_STAT_API_BASE}/json/test"
    assert params["appId"] == "dummy"
    assert params["x"] == "1"
    assert timeout == stats.DEFAULT_TIMEOUT
    assert data is None


@pytest.mark.asyncio
async def test_make_request_raises_for_estat_json_error(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        json_data={
            "GET_STATS_DATA": {
                "RESULT": {
                    "STATUS": 100,
                    "ERROR_MSG": "パラメータが正しくありません。",
                }
            }
        }
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    with pytest.raises(stats.EStatAPIError, match="100"):
        await stats._make_request("json/getStatsData", {"x": "1"})


@pytest.mark.asyncio
async def test_make_request_returns_csv_with_post(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(text="csv-content")
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await stats._make_request(
        "csv/test", {"x": "1"}, method="POST", format="csv", data={"foo": "bar"}
    )
    assert result == "csv-content"

    assert len(client.calls) == 1
    method, url, params, data, timeout = client.calls[0]
    assert method == "POST"
    assert url == f"{stats.E_STAT_API_BASE}/csv/test"
    assert params is None
    assert data == {"appId": "dummy", "x": "1", "foo": "bar"}
    assert timeout == stats.DEFAULT_TIMEOUT


@pytest.mark.asyncio
async def test_get_stats_data_bulk_posts_stats_datas_spec(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(json_data={"GET_STATS_DATAS": {"RESULT": {"STATUS": 0}}})
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await stats.get_stats_data_bulk(
        requests=[
            {"statsDataId": "0001", "limit": 10},
            {"dataSetId": "dataset-1", "cdArea": "13000"},
        ]
    )
    assert result == {"GET_STATS_DATAS": {"RESULT": {"STATUS": 0}}}

    method, url, params, data, timeout = client.calls[0]
    assert method == "POST"
    assert url == f"{stats.E_STAT_API_BASE}/json/getStatsDatas"
    assert params is None
    assert "statsDatasSpec" in data
    assert data["appId"] == "dummy"
    assert data["lang"] == "J"
    assert json.loads(data["statsDatasSpec"]) == [
        {"statsDataId": "0001", "limit": "10"},
        {"dataSetId": "dataset-1", "cdArea": "13000"},
    ]
    assert timeout == stats.DEFAULT_TIMEOUT


@pytest.mark.asyncio
async def test_get_stats_data_bulk_keeps_legacy_id_inputs(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(json_data={"GET_STATS_DATAS": {"RESULT": {"STATUS": 0}}})
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    await stats.get_stats_data_bulk(
        stats_data_ids=["0001"],
        dataset_ids=["ds1"],
        start_position=1,
        limit=5,
    )

    _, _, _, data, _ = client.calls[0]
    assert json.loads(data["statsDatasSpec"]) == [
        {"statsDataId": "0001", "startPosition": "1", "limit": "5"},
        {"dataSetId": "ds1", "startPosition": "1", "limit": "5"},
    ]


@pytest.mark.asyncio
async def test_get_stats_data_bulk_rejects_malformed_requests(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    with pytest.raises(ValueError, match="statsDataId"):
        await stats.get_stats_data_bulk(requests=[{"limit": 5}])
    with pytest.raises(ValueError, match="どちらか一方"):
        await stats.get_stats_data_bulk(
            requests=[{"statsDataId": "0001", "dataSetId": "ds1"}]
        )
    with pytest.raises(ValueError, match="1以上"):
        await stats.get_stats_data_bulk(requests=[{"statsDataId": "0001", "limit": 0}])
    with pytest.raises(ValueError, match="1以上"):
        await stats.get_stats_data_bulk(
            requests=[{"statsDataId": "0001", "limit": 1.5}]
        )


@pytest.mark.asyncio
async def test_get_stats_data_bulk_omits_empty_request_values(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(json_data={"GET_STATS_DATAS": {"RESULT": {"STATUS": 0}}})
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    await stats.get_stats_data_bulk(
        requests=[{"statsDataId": "", "dataSetId": "ds1", "cdArea": ""}]
    )

    _, _, _, data, _ = client.calls[0]
    assert json.loads(data["statsDatasSpec"]) == [{"dataSetId": "ds1"}]


@pytest.mark.asyncio
async def test_post_dataset_posts_dataset_name_and_parses_xml(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        text="""<?xml version="1.0" encoding="utf-8"?>
<POST_DATASET>
  <RESULT>
    <STATUS>0</STATUS>
    <ERROR_MSG>正常に終了しました。</ERROR_MSG>
    <DATE>2026-05-14T12:00:00.000+09:00</DATE>
  </RESULT>
  <PARAMETER>
    <LANG>J</LANG>
    <STATS_DATA_ID>0001</STATS_DATA_ID>
    <DATASET_NAME>sample</DATASET_NAME>
    <NARROWING_COND>
      <CODE_CAT01_SELECT>000</CODE_CAT01_SELECT>
    </NARROWING_COND>
    <PROCESS_MODE>E</PROCESS_MODE>
  </PARAMETER>
  <REGIST_INF mode="add">
    <DATASET_ID>dataset-1</DATASET_ID>
    <STATS_DATA_ID>0001</STATS_DATA_ID>
    <PUBLIC_STATE>yes</PUBLIC_STATE>
    <TOTAL_NUMBER>2</TOTAL_NUMBER>
  </REGIST_INF>
</POST_DATASET>"""
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await dataset.post_dataset(
        dataset_name="sample",
        stats_data_id="0001",
        conditions={"codeCat01Select": "000"},
    )

    assert result["result"]["status"] == "0"
    assert result["parameter"]["dataset_name"] == "sample"
    assert result["parameter"]["narrowing_cond"]["code_cat01_select"] == "000"
    assert result["dataset"] == {
        "mode": "add",
        "dataset_id": "dataset-1",
        "stats_data_id": "0001",
        "public_state": "yes",
        "total_number": "2",
    }

    method, url, params, data, _ = client.calls[0]
    assert method == "POST"
    assert url == f"{stats.E_STAT_API_BASE}/postDataset"
    assert params is None
    assert data["dataSetName"] == "sample"
    assert data["appId"] == "dummy"
    assert data["processMode"] == "E"
    assert "datasetName" not in data


@pytest.mark.asyncio
async def test_post_dataset_delete_mode_only_requires_dataset_id(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        text="""<?xml version="1.0" encoding="utf-8"?>
<POST_DATASET>
  <RESULT>
    <STATUS>0</STATUS>
    <ERROR_MSG>正常に終了しました。</ERROR_MSG>
  </RESULT>
  <REGIST_INF mode="delete">
    <DATASET_ID>dataset-1</DATASET_ID>
  </REGIST_INF>
</POST_DATASET>"""
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await dataset.post_dataset(
        data_set_id="dataset-1",
        process_mode="D",
    )

    assert result["dataset"]["mode"] == "delete"
    _, _, params, data, _ = client.calls[0]
    assert params is None
    assert data["dataSetId"] == "dataset-1"
    assert data["processMode"] == "D"
    assert "statsDataId" not in data
    assert "dataSetName" not in data


def test_post_dataset_validates_mode_requirements():
    with pytest.raises(ValueError, match="stats_data_id"):
        dataset._validate_post_dataset_args(
            process_mode="E",
            stats_data_id=None,
            data_set_id=None,
        )
    with pytest.raises(ValueError, match="data_set_id"):
        dataset._validate_post_dataset_args(
            process_mode="D",
            stats_data_id=None,
            data_set_id=None,
        )


def test_post_dataset_conditions_cannot_override_control_params():
    with pytest.raises(ValueError, match="processMode"):
        dataset._validate_post_dataset_conditions({"processMode": "D"})


@pytest.mark.asyncio
async def test_get_dataset_params_reject_invalid_paging(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    with pytest.raises(ValueError, match="start_position"):
        await dataset.get_dataset(start_position=0)


@pytest.mark.asyncio
async def test_get_dataset_maps_params_to_ref_dataset(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(json_data={"REF_DATASET": {"RESULT": {"STATUS": 0}}})
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await dataset.get_dataset(
        dataset_id="CTCdemo-kokusei1",
        start_position=1,
        limit=1,
    )

    assert result == {"REF_DATASET": {"RESULT": {"STATUS": 0}}}
    method, url, params, data, timeout = client.calls[0]
    assert method == "GET"
    assert url == f"{stats.E_STAT_API_BASE}/json/refDataset"
    assert params == {
        "appId": "dummy",
        "dataSetId": "CTCdemo-kokusei1",
    }
    assert data is None
    assert timeout == stats.DEFAULT_TIMEOUT


@pytest.mark.asyncio
async def test_get_dataset_applies_list_paging_locally(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        json_data={
            "GET_DATASET_LIST": {
                "RESULT": {"STATUS": 0},
                "PARAMETER": {"LANG": "J", "DATA_FORMAT": "J"},
                "DATASET_LIST_INF": {
                    "NUMBER": 20,
                    "DATASET_INF": [
                        {"DATASET_ID": "ds1"},
                        {"DATASET_ID": "ds2"},
                    ],
                },
            }
        }
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await dataset.get_dataset(start_position=1, limit=1)

    method, url, params, data, _ = client.calls[0]
    assert method == "GET"
    assert url == f"{stats.E_STAT_API_BASE}/json/refDataset"
    assert params == {"appId": "dummy"}
    assert data is None

    dataset_list = result["GET_DATASET_LIST"]
    assert dataset_list["PARAMETER"]["START_POSITION"] == "1"
    assert dataset_list["PARAMETER"]["LIMIT"] == "1"
    assert dataset_list["DATASET_LIST_INF"]["NUMBER"] == 1
    assert dataset_list["DATASET_LIST_INF"]["DATASET_INF"] == [{"DATASET_ID": "ds1"}]


@pytest.mark.asyncio
async def test_data_catalog_params_reject_invalid_paging(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    with pytest.raises(ValueError, match="limit"):
        await catalog.get_data_catalog(limit=0)
    with pytest.raises(ValueError, match="start_position"):
        await catalog.get_data_catalog_csv(start_position=0)


@pytest.mark.asyncio
async def test_get_data_catalog_csv_uses_json_endpoint_and_converts(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        json_data={
            "GET_DATA_CATALOG": {
                "RESULT": {"STATUS": 0},
                "DATA_CATALOG_LIST_INF": {
                    "DATA_CATALOG_INF": [
                        {
                            "STAT_NAME": {"@code": "00200524", "$": "国勢調査"},
                            "TITLE": "sample, title",
                            "DATA_FORMAT": "XLS",
                        }
                    ]
                },
            }
        }
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await catalog.get_data_catalog_csv(stats_code="00200524", limit=1)

    method, url, params, data, timeout = client.calls[0]
    assert method == "GET"
    assert url == f"{stats.E_STAT_API_BASE}/json/getDataCatalog"
    assert params == {"appId": "dummy", "statsCode": "00200524", "limit": "1"}
    assert data is None
    assert timeout == stats.DEFAULT_TIMEOUT

    assert "DATA_FORMAT" in result
    assert "STAT_NAME.$" in result
    assert "STAT_NAME.@code" in result
    assert '"sample, title"' in result


@pytest.mark.asyncio
async def test_get_data_catalog_csv_adds_guidance_for_broad_search(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        json_data={
            "GET_DATA_CATALOG": {
                "RESULT": {"STATUS": 0},
                "DATA_CATALOG_LIST_INF": {
                    "NUMBER": 9912,
                    "DATA_CATALOG_INF": [{"TITLE": "交通事故の発生状況"}],
                },
            }
        }
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await catalog.get_data_catalog_csv(search_word="人口", limit=1)

    assert isinstance(result, dict)
    assert "TITLE" in result["csv"]
    guidance = result[catalog.CATALOG_GUIDANCE_KEY]
    assert guidance["code"] == "DATA_CATALOG_QUERY_TOO_BROAD"
    assert guidance["retryable"] is True
    assert guidance["matched_count_hint"] == 9912
    assert guidance["suggested_next_calls"][0]["tool"] == "get_stats_list"


@pytest.mark.asyncio
async def test_get_data_catalog_adds_guidance_for_broad_search(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        json_data={
            "GET_DATA_CATALOG": {
                "RESULT": {"STATUS": 0},
                "PARAMETER": {"SEARCH_WORD": "人口", "LIMIT": "1"},
                "DATA_CATALOG_LIST_INF": {
                    "NUMBER": 9912,
                    "RESULT_INF": {"FROM_NUMBER": 1, "TO_NUMBER": 1},
                    "DATA_CATALOG_INF": [{"TITLE": "交通事故の発生状況"}],
                },
            }
        }
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    result = await catalog.get_data_catalog(search_word="人口", limit=1)

    guidance = result[catalog.CATALOG_GUIDANCE_KEY]
    assert guidance["code"] == "DATA_CATALOG_QUERY_TOO_BROAD"
    assert guidance["retryable"] is True
    assert guidance["matched_count_hint"] == 9912
    assert guidance["suggested_next_calls"][0]["tool"] == "get_stats_list"


@pytest.mark.asyncio
async def test_get_data_catalog_returns_recovery_result_on_timeout(monkeypatch):
    async def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(catalog, "_make_request", raise_timeout)

    result = await catalog.get_data_catalog(search_word="人口", limit=1)

    assert result["isError"] is True
    error = result["structuredContent"]["error"]
    assert error["code"] == "UPSTREAM_TIMEOUT_QUERY_TOO_BROAD"
    assert error["retryable"] is True
    assert error["suggested_next_calls"][0]["tool"] == "get_stats_list"


@pytest.mark.asyncio
async def test_get_data_catalog_csv_returns_recovery_result_on_timeout(monkeypatch):
    async def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(catalog, "_make_request", raise_timeout)

    result = await catalog.get_data_catalog_csv(search_word="人口", limit=1)

    assert isinstance(result, dict)
    assert result["isError"] is True
    assert (
        result["structuredContent"]["error"]["suggested_next_calls"][0]["tool"]
        == "get_stats_list"
    )


@pytest.mark.asyncio
async def test_read_only_tools_have_annotations():
    tools = {tool.name: tool for tool in await server_main.mcp.list_tools()}

    assert tools["get_data_catalog"].annotations.readOnlyHint is True
    assert tools["get_data_catalog_csv"].annotations.readOnlyHint is True
    assert tools["get_stats_list"].annotations.readOnlyHint is True
    assert tools["post_dataset"].annotations is None


def test_parse_post_dataset_xml_ignores_namespaces():
    result = dataset._parse_post_dataset_xml(
        """<?xml version="1.0" encoding="utf-8"?>
<estat:POST_DATASET xmlns:estat="urn:estat">
  <estat:RESULT>
    <estat:STATUS>0</estat:STATUS>
    <estat:ERROR_MSG>正常に終了しました。</estat:ERROR_MSG>
  </estat:RESULT>
  <estat:PARAMETER>
    <estat:DATASET_NAME>sample</estat:DATASET_NAME>
  </estat:PARAMETER>
  <estat:REGIST_INF mode="add">
    <estat:DATASET_ID>dataset-1</estat:DATASET_ID>
  </estat:REGIST_INF>
</estat:POST_DATASET>"""
    )

    assert result["result"]["status"] == "0"
    assert result["parameter"]["dataset_name"] == "sample"
    assert result["dataset"]["dataset_id"] == "dataset-1"


@pytest.mark.asyncio
async def test_post_dataset_raises_for_xml_error(monkeypatch):
    monkeypatch.setenv("E_STAT_APP_ID", "dummy")
    response = DummyResponse(
        text="""<?xml version="1.0" encoding="utf-8"?>
<POST_DATASET>
  <RESULT>
    <STATUS>100</STATUS>
    <ERROR_MSG>必須パラメータがありません。</ERROR_MSG>
  </RESULT>
</POST_DATASET>"""
    )
    client = DummyClient(response)

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(stats.httpx, "AsyncClient", factory)

    with pytest.raises(stats.EStatAPIError, match="100"):
        await dataset.post_dataset(dataset_name="sample", stats_data_id="0001")
