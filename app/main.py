from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.calculator import project_avd_growth, project_without_subsidy, years_to_retirement
from app.models import (
    AvdCalculationRequest,
    AvdCalculationResponse,
    PhoneSignupRequest,
    PhoneSignupResponse,
)

load_dotenv()

app = FastAPI(
    title="Altersvorsorgedepot Calculator API",
    version="2.0.0",
    description=(
        "API for a ChatGPT Altersvorsorgedepot assistant with subsidy simulation "
        "and phone-based account signup CTA."
    ),
)

BASE_DIR = Path(__file__).resolve().parent
SIGNUP_BASE_URL = os.getenv("BANK_SIGNUP_BASE_URL", "https://bank.example.com/signup")

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


def _is_e164(phone_number: str) -> bool:
    return bool(re.fullmatch(r"\+[1-9]\d{7,14}", phone_number))


@app.post("/signup/phone", response_model=PhoneSignupResponse)
def create_phone_signup(payload: PhoneSignupRequest) -> PhoneSignupResponse:
    phone_number = payload.phone_number.strip()
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Explicit consent is required")

    if not _is_e164(phone_number):
        raise HTTPException(status_code=400, detail="Phone number must be in E.164 format")

    query = urlencode(
        {
            "phone": phone_number,
            "source": payload.source,
            "entry": "altersvorsorgedepot-calculator",
        }
    )
    signup_url = f"{SIGNUP_BASE_URL}?{query}"

    return PhoneSignupResponse(
        signup_url=signup_url,
        cta="Continue with phone signup and open your account",
    )

