from typing import Any

import pytest

from e_stats_mcp.tools import stats


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

    async def __aenter__(self) -> "DummyClient":
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
    assert params["appId"] == "dummy"
    assert params["x"] == "1"
    assert data == {"foo": "bar"}
    assert timeout == stats.DEFAULT_TIMEOUT

