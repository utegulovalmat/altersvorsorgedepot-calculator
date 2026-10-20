from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
import uvicorn

from app.calculator import project_avd_growth, project_without_subsidy, years_to_retirement
from app.models import AvdCalculationRequest, AvdCalculationResponse, AvdWidgetResponse

WIDGET_URI = "ui://avd/calculator-v2.html"
STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"

mcp = FastMCP(
    "altersvorsorgedepot-calculator",
    instructions=(
        "Use show_avd_calculator when a user asks about ETF retirement savings, "
        "Germany's Altersvorsorgedepot, or government subsidy projections. "
        "The widget lets the user adjust assumptions and has an external Trade Republic registration button."
    ),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "avd-calculator-mcp.onrender.com",
            "avd-calculator-mcp.onrender.com:*",
            "localhost",
            "localhost:*",
            "127.0.0.1",
            "127.0.0.1:*",
        ],
        allowed_origins=[
            "https://avd-calculator-mcp.onrender.com",
            "https://chatgpt.com",
            "https://chat.openai.com",
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
    ),
)


def calculate(payload: AvdCalculationRequest) -> AvdCalculationResponse:
    horizon_years = years_to_retirement(payload)
    if horizon_years <= 0:
        raise ValueError("retirement_age must be greater than current_age")

    projected_value, total_contributed, total_subsidy, estimated_growth, yearly_projection = project_avd_growth(payload)
    projected_without_subsidy = project_without_subsidy(payload)

    return AvdCalculationResponse(
        years_to_retirement=horizon_years,
        total_contributed=total_contributed,
        total_government_subsidy=total_subsidy,
        projected_value=projected_value,
        projected_value_without_subsidy=projected_without_subsidy,
        subsidy_value_uplift=round(projected_value - projected_without_subsidy, 2),
        estimated_market_growth=estimated_growth,
        yearly_projection=yearly_projection,
        disclaimer=(
            "Illustrative model based on 2027 Altersvorsorgedepot subsidy assumptions. "
            "Not investment, tax, or legal advice."
        ),
    )


@mcp.resource(
    WIDGET_URI,
    name="AVD calculator widget",
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "prefersBorder": True,
            "csp": {"connectDomains": [], "resourceDomains": []},
        },
        "openai/widgetCSP": {
            "connect_domains": [],
            "resource_domains": [],
            "redirect_domains": ["https://traderepublic.com"],
        },
        "openai/widgetDescription": "Interactive Altersvorsorgedepot calculator with a Trade Republic registration link.",
    },
)
def avd_calculator_widget() -> str:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    css = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")
    javascript = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    return html.replace('<link rel="stylesheet" href="/static/styles.css" />', f"<style>{css}</style>").replace(
        '<script src="/static/app.js"></script>', f"<script>{javascript}</script>"
    )


@mcp.tool(
    title="Calculate Altersvorsorgedepot",
    description="Calculate a German Altersvorsorgedepot projection with and without subsidy. Returns data without opening a new widget.",
    structured_output=True,
)
def calculate_altersvorsorgedepot(
    current_age: int,
    retirement_age: int,
    monthly_contribution: float,
    expected_annual_return_pct: float = 6.0,
    annual_cost_pct: float = 0.8,
    eligible_children: int = 0,
    include_starter_bonus: bool = True,
) -> AvdCalculationResponse:
    payload = AvdCalculationRequest(
        current_age=current_age,
        retirement_age=retirement_age,
        monthly_contribution=monthly_contribution,
        expected_annual_return_pct=expected_annual_return_pct,
        annual_cost_pct=annual_cost_pct,
        eligible_children=eligible_children,
        include_starter_bonus=include_starter_bonus,
    )
    return calculate(payload)


@mcp.tool(
    title="Show interactive AVD calculator",
    description=(
        "Open the single interactive Altersvorsorgedepot calculator widget for ETF retirement questions. "
        "Users can change inputs themselves and click through to Trade Republic to register."
    ),
    meta={
        "ui": {"resourceUri": WIDGET_URI},
        "openai/outputTemplate": WIDGET_URI,
    },
    structured_output=True,
)
def show_avd_calculator(
    current_age: int = 30,
    retirement_age: int = 67,
    monthly_contribution: float = 150,
    expected_annual_return_pct: float = 6.0,
    annual_cost_pct: float = 0.8,
    eligible_children: int = 0,
    include_starter_bonus: bool = True,
) -> AvdWidgetResponse:
    payload = AvdCalculationRequest(
        current_age=current_age,
        retirement_age=retirement_age,
        monthly_contribution=monthly_contribution,
        expected_annual_return_pct=expected_annual_return_pct,
        annual_cost_pct=annual_cost_pct,
        eligible_children=eligible_children,
        include_starter_bonus=include_starter_bonus,
    )
    return AvdWidgetResponse(inputs=payload, **calculate(payload).model_dump())


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip()
    if transport == "streamable-http":
        app = mcp.streamable_http_app()

        async def health(_request):
            return JSONResponse({"status": "ok"})

        app.add_route("/health", health, methods=["GET"])
        uvicorn.run(app, host=os.getenv("MCP_HOST", "0.0.0.0"), port=int(os.getenv("MCP_PORT", os.getenv("PORT", "8001"))))
    else:
        mcp.run()
