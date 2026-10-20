from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.calculator import project_avd_growth, project_without_subsidy, years_to_retirement
from app.models import (
    AvdCalculationRequest,
    AvdCalculationResponse,
)

load_dotenv()

app = FastAPI(
    title="Altersvorsorgedepot Calculator API",
    version="2.0.0",
    description=(
        "API for a ChatGPT Altersvorsorgedepot assistant with subsidy simulation "
        "and a direct Trade Republic registration link."
    ),
)

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def calculator_ui() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/avd/calculate", response_model=AvdCalculationResponse)
def calculate_altersvorsorgedepot(payload: AvdCalculationRequest) -> AvdCalculationResponse:
    years = years_to_retirement(payload)
    if years <= 0:
        raise HTTPException(status_code=400, detail="Retirement age must be higher than current age")

    projected_value, total_contributed, total_subsidy, estimated_growth, yearly_projection = project_avd_growth(payload)
    projected_without_subsidy = project_without_subsidy(payload)

    return AvdCalculationResponse(
        years_to_retirement=years,
        total_contributed=total_contributed,
        total_government_subsidy=total_subsidy,
        projected_value=projected_value,
        projected_value_without_subsidy=projected_without_subsidy,
        subsidy_value_uplift=round(projected_value - projected_without_subsidy, 2),
        estimated_market_growth=estimated_growth,
        yearly_projection=yearly_projection,
        disclaimer=(
            "Illustrative model based on 2027 Altersvorsorgedepot subsidy assumptions. "
            "This is not investment, tax, or legal advice."
        ),
    )

