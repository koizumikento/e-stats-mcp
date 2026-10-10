"""Export authoritative Python tool definitions and synthetic parity fixtures."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import httpx

from e_stats_mcp import __version__, mcp, tools
from e_stats_mcp.settings import Settings
from e_stats_mcp.tools.stats_fields import STATS_FIELDS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".sites-generated"


async def export() -> None:
    OUTPUT.mkdir(exist_ok=True)
    definitions = [
        tool.to_mcp_tool().model_dump(mode="json", by_alias=True, exclude_none=True)
        for tool in await mcp.list_tools()
    ]
    write(
        "contract.json",
        {
            "version": __version__,
            "instructions": mcp.instructions,
            "tools": definitions,
            "fields": STATS_FIELDS,
        },
    )
    cases = json.loads((ROOT / "sites-tests/cases.json").read_text(encoding="utf-8"))
    for case in cases:
        calls = []

        async def respond(
            request: httpx.Request, case=case, calls=calls
        ) -> httpx.Response:
            calls.append(
                {
                    "method": request.method,
                    "url": str(request.url),
                    "body": request.content.decode(),
                }
            )
            if case.get("timeout"):
                raise httpx.ReadTimeout("fixture timeout")
            payload = case.get("upstream", {})
            return (
                httpx.Response(200, json=payload)
                if isinstance(payload, dict)
                else httpx.Response(200, text=payload)
            )

        # No network or environment secrets: exercise the existing HTTP code too.
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with (
            patch("e_stats_mcp.tools.stats.httpx.AsyncClient", return_value=client),
            patch(
                "e_stats_mcp.tools.stats.get_settings",
                return_value=Settings(E_STAT_APP_ID="fixture-only"),
            ),
        ):
            try:
                case["expected"] = await getattr(tools, case["tool"])(
                    **case["arguments"]
                )
            except (ValueError, TypeError) as error:
                case["expected_error"] = str(error)
            finally:
                await client.aclose()
        case["calls"] = calls
    write("fixtures.json", cases)


def write(name: str, value: object) -> None:
    (OUTPUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(export())
