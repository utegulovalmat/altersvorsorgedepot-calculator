"""Exercise the ChatGPT widget through the MCP transport."""

import os
from pathlib import Path
import sys
import unittest
from html.parser import HTMLParser

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
WIDGET_URI = "ui://avd/calculator-v2.html"
REGISTRATION_URL = "https://traderepublic.com/de-de"


class RegistrationLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("id") == "register-link":
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
                self.assertEqual(tools["show_avd_calculator"].meta["ui"]["resourceUri"], WIDGET_URI)
                self.assertTrue(tools["show_avd_calculator"].outputSchema)
                self.assertTrue(tools["calculate_altersvorsorgedepot"].outputSchema)
                self.assertFalse(tools["calculate_altersvorsorgedepot"].meta)

                opened = await session.call_tool("show_avd_calculator", {})
                self.assertFalse(opened.isError)
                self.assertEqual(opened.structuredContent["inputs"]["current_age"], 30)
                self.assertEqual(len(opened.structuredContent["yearly_projection"]), 37)

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
                self.assertFalse(result.isError)
                self.assertEqual(result.structuredContent["projected_value"], 81900)
                self.assertEqual(result.structuredContent["total_government_subsidy"], 18900)

                invalid = await session.call_tool(
                    "calculate_altersvorsorgedepot",
                    {"current_age": 65, "retirement_age": 63, "monthly_contribution": 150},
                )
                self.assertTrue(invalid.isError)

                resource = (await session.read_resource(WIDGET_URI)).contents[0]
                self.assertEqual(resource.mimeType, "text/html;profile=mcp-app")
                self.assertEqual(resource.meta["openai/widgetCSP"]["redirect_domains"], ["https://traderepublic.com"])
                parser = RegistrationLinkParser()
                parser.feed(resource.text)
                self.assertEqual(parser.link["href"], REGISTRATION_URL)
                self.assertIn("noopener", parser.link["rel"])
                self.assertIn("tools/call", resource.text)
                self.assertIn('class="calculator"', resource.text)
                self.assertIn('id="metric-without-subsidy"', resource.text)
                self.assertNotIn('src="/static/', resource.text)
                self.assertNotIn('id="signup-form"', resource.text)


if __name__ == "__main__":
    unittest.main()
