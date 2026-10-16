from __future__ import annotations

from app.models import AvdCalculationRequest, ProjectionYear


MAX_ELIGIBLE_SUBSIDY_CONTRIBUTION = 1_800
MAX_TOTAL_ANNUAL_CONTRIBUTION = 6_840
BASE_SUBSIDY_TIER_ONE_CAP = 360
BASE_SUBSIDY_TIER_ONE_RATE = 0.50
BASE_SUBSIDY_TIER_TWO_RATE = 0.25
CHILD_SUBSIDY_MAX_PER_CHILD = 300
STARTER_BONUS = 200


def years_to_retirement(payload: AvdCalculationRequest) -> int:
    return payload.retirement_age - payload.current_age


def annual_subsidy_for_contribution(
    annual_contribution: float,
    eligible_children: int,
    starter_bonus: bool,
    year: int,
) -> float:
    eligible_contribution = min(annual_contribution, MAX_ELIGIBLE_SUBSIDY_CONTRIBUTION)

    tier_one = min(eligible_contribution, BASE_SUBSIDY_TIER_ONE_CAP) * BASE_SUBSIDY_TIER_ONE_RATE
    tier_two_base = max(eligible_contribution - BASE_SUBSIDY_TIER_ONE_CAP, 0)
    tier_two = tier_two_base * BASE_SUBSIDY_TIER_TWO_RATE
    base_subsidy = tier_one + tier_two

    child_subsidy_per_child = min(eligible_contribution, CHILD_SUBSIDY_MAX_PER_CHILD)
    child_subsidy = child_subsidy_per_child * max(eligible_children, 0)

    starter = STARTER_BONUS if starter_bonus and year == 1 else 0
    return base_subsidy + child_subsidy + starter

def project_avd_growth(payload: AvdCalculationRequest) -> tuple[float, float, float, float, list[ProjectionYear]]:
    years = years_to_retirement(payload)
    annual_return = payload.expected_annual_return_pct / 100
    annual_fee = payload.annual_cost_pct / 100
    net_annual_return = max(annual_return - annual_fee, 0)
    monthly_rate = (1 + net_annual_return) ** (1 / 12) - 1

    months = years * 12
    annual_contribution = min(payload.monthly_contribution * 12, MAX_TOTAL_ANNUAL_CONTRIBUTION)
    monthly_contribution = annual_contribution / 12

    balance = 0.0
    total_contributed = 0.0
    total_subsidy = 0.0
    starter_bonus_active = payload.include_starter_bonus and payload.current_age < 25

    yearly_projection: list[ProjectionYear] = []
    for month in range(1, months + 1):
        balance = (balance + monthly_contribution) * (1 + monthly_rate)
        total_contributed += monthly_contribution

        if month % 12 == 0:
            year_index = month // 12
            subsidy = annual_subsidy_for_contribution(
                annual_contribution=annual_contribution,
                eligible_children=payload.eligible_children,
                starter_bonus=starter_bonus_active,
                year=year_index,
            )
            total_subsidy += subsidy
            balance += subsidy

            yearly_projection.append(
                ProjectionYear(
                    year=year_index,
                    age=payload.current_age + year_index,
                    end_balance=round(balance, 2),
                    total_contributed=round(total_contributed, 2),
                    government_subsidy_year=round(subsidy, 2),
                )
            )

    projected_value = round(balance, 2)
    total_contributed = round(total_contributed, 2)
    total_subsidy = round(total_subsidy, 2)
    estimated_growth = round(projected_value - total_contributed - total_subsidy, 2)
    return projected_value, total_contributed, total_subsidy, estimated_growth, yearly_projection


def project_without_subsidy(payload: AvdCalculationRequest) -> float:
    years = years_to_retirement(payload)
    annual_return = payload.expected_annual_return_pct / 100
    annual_fee = payload.annual_cost_pct / 100
    net_annual_return = max(annual_return - annual_fee, 0)
    monthly_rate = (1 + net_annual_return) ** (1 / 12) - 1

    annual_contribution = min(payload.monthly_contribution * 12, MAX_TOTAL_ANNUAL_CONTRIBUTION)
    monthly_contribution = annual_contribution / 12
    months = years * 12

    balance = 0.0
    for _ in range(months):
        balance = (balance + monthly_contribution) * (1 + monthly_rate)

    return round(balance, 2)

