from __future__ import annotations

import os
from urllib.parse import urlencode

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
import uvicorn

from app.calculator import project_avd_growth, project_without_subsidy, years_to_retirement
from app.models import AvdCalculationRequest

mcp = MCPServer("altersvorsorgedepot-calculator")
SIGNUP_BASE_URL = os.getenv("BANK_SIGNUP_BASE_URL", "https://bank.example.com/signup")


@mcp.tool()
def calculate_altersvorsorgedepot(
    current_age: int,
    retirement_age: int,
    monthly_contribution: float,
    expected_annual_return_pct: float = 6.0,
    annual_cost_pct: float = 0.8,
    eligible_children: int = 0,
    include_starter_bonus: bool = True,
) -> dict:
    """Calculate Altersvorsorgedepot potential savings including government subsidy."""
    payload = AvdCalculationRequest(
        current_age=current_age,
        retirement_age=retirement_age,
        monthly_contribution=monthly_contribution,
        expected_annual_return_pct=expected_annual_return_pct,
        annual_cost_pct=annual_cost_pct,
        eligible_children=eligible_children,
        include_starter_bonus=include_starter_bonus,
    )

    horizon_years = years_to_retirement(payload)
    if horizon_years <= 0:
        raise ValueError("retirement_age must be greater than current_age")

    projected_value, total_contributed, total_subsidy, estimated_growth, yearly_projection = project_avd_growth(payload)
    projected_without_subsidy = project_without_subsidy(payload)

    return {
        "years_to_retirement": horizon_years,
        "total_contributed": total_contributed,
        "total_government_subsidy": total_subsidy,
        "projected_value": projected_value,
        "projected_value_without_subsidy": projected_without_subsidy,
        "subsidy_value_uplift": round(projected_value - projected_without_subsidy, 2),
        "estimated_market_growth": estimated_growth,
        "yearly_projection": [item.model_dump() for item in yearly_projection],
        "disclaimer": (
            "Illustrative model based on 2027 Altersvorsorgedepot subsidy assumptions. "
            "Not investment, tax, or legal advice."
        ),
    }


@mcp.tool()
def create_phone_signup_link(phone_number: str, source: str = "chatgpt-mcp") -> dict:
    """Build a signup URL for phone-based account opening."""
    query = urlencode(
        {
            "phone": phone_number.strip(),
            "source": source,
            "entry": "altersvorsorgedepot-calculator",
        }
    )
    signup_url = f"{SIGNUP_BASE_URL}?{query}"
    return {
        "signup_url": signup_url,
        "cta": "Continue with phone signup and open your account",
    }


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip()
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", os.getenv("PORT", "8001")))

        app = mcp.streamable_http_app(
            streamable_http_path="/mcp",
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

        async def health(_request):
            return JSONResponse({"status": "ok"})

        app.add_route("/health", health, methods=["GET"])
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()
