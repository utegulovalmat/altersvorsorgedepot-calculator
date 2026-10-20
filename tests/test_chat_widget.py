"""Exercise the widget contract through the real MCP transport."""

import os
from pathlib import Path
import sys
import unittest
from html.parser import HTMLParser

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


ROOT = Path(__file__).resolve().parents[1]
URI = "ui://widget/altersvorsorgedepot-v1.html"
FUNDING_URL = "https://traderepublic.com/de-de/altersvorsorgedepot"


class FundingLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("id") == "funding-link":
            self.link = attrs


class ChatWidgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_widget_discovery_and_calculation(self):
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(ROOT / "mcp_server.py")],
            cwd=str(ROOT),
            env={**os.environ, "MCP_TRANSPORT": "stdio"},
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                for name in (
                    "open_altersvorsorgedepot_calculator",
                    "calculate_altersvorsorgedepot",
                ):
                    self.assertEqual(tools[name].meta["openai/outputTemplate"], URI)
                    self.assertTrue(tools[name].meta["openai/widgetAccessible"])
                    self.assertTrue(tools[name].annotations.read_only_hint)

                opened = await session.call_tool("open_altersvorsorgedepot_calculator", {})
                self.assertFalse(opened.is_error)
                self.assertEqual(opened.structured_content["inputs"]["current_age"], 30)
                self.assertEqual(len(opened.structured_content["yearly_projection"]), 37)

                result = await session.call_tool(
                    "calculate_altersvorsorgedepot",
                    {
                        "current_age": 30,
                        "retirement_age": 65,
                        "monthly_contribution": 150,
                        "expected_annual_return_pct": 0,
                        "annual_cost_pct": 0,
                    },
                )
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content["projected_value"], 81900)
                self.assertEqual(result.structured_content["total_government_subsidy"], 18900)
                invalid = await session.call_tool(
                    "calculate_altersvorsorgedepot",
                    {"current_age": 65, "retirement_age": 63, "monthly_contribution": 150},
                )
                self.assertTrue(invalid.is_error)

                resource = (await session.read_resource(URI)).contents[0]
                self.assertEqual(resource.mime_type, "text/html+skybridge")
                self.assertEqual(
                    resource.meta["openai/widgetCSP"]["redirect_domains"],
                    ["https://traderepublic.com"],
                )
                parser = FundingLinkParser()
                parser.feed(resource.text)
                self.assertEqual(parser.link["href"], FUNDING_URL)
                self.assertIn("noopener", parser.link["rel"])
                self.assertIn("Calculate funding</a>", resource.text)
                self.assertIn("window.openai.callTool", resource.text)
                self.assertNotIn('src="/static/', resource.text)
                self.assertNotIn('id="signup-form"', resource.text)


if __name__ == "__main__":
    unittest.main()
