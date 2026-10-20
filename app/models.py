from __future__ import annotations

from pydantic import BaseModel, Field


class AvdCalculationRequest(BaseModel):
    current_age: int = Field(..., ge=18, le=65, description="Current age in years")
    retirement_age: int = Field(..., ge=63, le=70, description="Planned retirement age")
    monthly_contribution: float = Field(..., ge=10, le=570, description="Monthly own contribution in EUR")
    expected_annual_return_pct: float = Field(6.0, ge=0, le=20, description="Expected annual return in percent")
    annual_cost_pct: float = Field(0.8, ge=0, le=3, description="Estimated total annual product costs in percent")
    eligible_children: int = Field(0, ge=0, le=10, description="Number of eligible children")
    include_starter_bonus: bool = Field(
        True,
        description="Apply one-time starter bonus if user is below 25",
    )


class ProjectionYear(BaseModel):
    year: int
    age: int
    end_balance: float
    total_contributed: float
    government_subsidy_year: float


class AvdCalculationResponse(BaseModel):
    years_to_retirement: int
    total_contributed: float
    total_government_subsidy: float
    projected_value: float
    projected_value_without_subsidy: float
    subsidy_value_uplift: float
    estimated_market_growth: float
    yearly_projection: list[ProjectionYear]
    disclaimer: str


class AvdWidgetResponse(AvdCalculationResponse):
    inputs: AvdCalculationRequest
