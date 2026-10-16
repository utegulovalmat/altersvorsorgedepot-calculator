# Altersvorsorgedepot Calculator + Signup Funnel (ChatGPT + MCP)

This project is an MVP for a German **Altersvorsorgedepot** assistant.

It includes:
1. a web calculator UI (mechanics inspired by Altersvorsorgedepot calculators)
2. a FastAPI backend for subsidy + projection math
3. a phone-signup CTA endpoint for account opening
4. an MCP server so ChatGPT can call the calculator as tools

## What is implemented

### 1) Calculator API

- `POST /avd/calculate`
- Inputs:
  - `current_age`, `retirement_age`
  - `monthly_contribution`
  - `expected_annual_return_pct`, `annual_cost_pct`
  - `eligible_children`, `include_starter_bonus`
- Output:
  - projected end capital
  - own contributions
  - total government subsidy
  - value uplift from subsidy
  - yearly projection

### 2) Subsidy mechanics used

Current model assumptions (2027 law-style mechanics, configurable in code):

- Contribution cap in product: **6,840 €/year**
- Subsidy-eligible contribution: **up to 1,800 €/year**
- Base subsidy:
  - **50%** on first **360 €** contribution
  - **25%** on next **1,440 €** contribution
  - max base subsidy: **540 €/year**
- Child subsidy:
  - up to **300 €/child/year**
  - modeled as `min(eligible_contribution, 300) * number_of_children`
- Starter bonus:
  - one-time **200 €** when starting before 25 (if enabled)

Important: this is an illustrative model, not legal/tax advice.

### 3) Phone signup funnel

- `POST /signup/phone`
- Requires E.164 phone format (example: `+491701234567`) and consent
- Returns a redirect URL to your bank signup page:
  - `BANK_SIGNUP_BASE_URL?phone=...&source=...&entry=altersvorsorgedepot-calculator`

### 4) Web UI

- `GET /` serves calculator page
- Focused conversion flow:
  - input assumptions
  - show projected result
  - ask for phone number
  - redirect to account opening

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open:
- `http://localhost:8000/`
- OpenAPI: `http://localhost:8000/openapi.json`

## MCP server run

### Local stdio (for local MCP clients)

```bash
python mcp_server.py
```

### Deployed Streamable HTTP MCP

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=8001 python mcp_server.py
```

MCP endpoint:
- `http://localhost:8001/mcp`

Exposed MCP tools:
- `calculate_altersvorsorgedepot`
- `create_phone_signup_link`

## Deploy options

### Option A: API + UI (FastAPI)

Use `Dockerfile`:

```bash
docker build -t avd-calculator-api .
docker run -p 8000:8000 --env-file .env avd-calculator-api
```

### Option B: MCP server (remote MCP)

Use `Dockerfile.mcp`:

```bash
docker build -f Dockerfile.mcp -t avd-calculator-mcp .
docker run -p 8001:8001 --env-file .env avd-calculator-mcp
```

For production, deploy on Render/Fly/Railway and expose HTTPS.

### One-click style Render setup

- `render.yaml` is included for two services:
  - `avd-calculator-api`
  - `avd-calculator-mcp`
- After import, set `BANK_SIGNUP_BASE_URL` in Render environment variables.

## Connect to ChatGPT

### As Action API (calculator app behavior)

1. Deploy FastAPI publicly via HTTPS
2. Create custom GPT
3. Add Action from `https://<your-domain>/openapi.json`
4. In GPT instructions:
   - call `/avd/calculate` when users ask for retirement-depot potential
   - show result with disclaimer
   - ask for confirmation, then call `/signup/phone`

### As MCP tools

1. Deploy `mcp_server.py` with streamable-http
2. Connect MCP endpoint in your MCP-compatible host
3. Use tools to calculate subsidy potential and generate signup links

## Compliance notes before going live

- Add legal review for subsidy assumptions and text
- Add GDPR-compliant consent logging for phone leads
- Add KYC/AML and suitability checks before account activation
- Avoid personalized regulated advice in assistant responses

