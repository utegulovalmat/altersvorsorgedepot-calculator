# Altersvorsorgedepot Calculator (ChatGPT + MCP)

This project is an MVP for a German **Altersvorsorgedepot** assistant.

It includes:
1. a web calculator UI (mechanics inspired by Altersvorsorgedepot calculators)
2. a FastAPI backend for subsidy + projection math
3. a **Calculate funding** button linking to Trade Republic (no phone collection in the UI)
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

### 3) Legacy phone signup API (not used by the calculator UI)

- `POST /signup/phone`
- Requires E.164 phone format (example: `+491701234567`) and consent
- Returns a redirect URL to your bank signup page:
  - `BANK_SIGNUP_BASE_URL?phone=...&source=...&entry=altersvorsorgedepot-calculator`

### 4) Web UI

- `GET /` serves calculator page
- Focused conversion flow:
  - input assumptions
  - show projected result
  - edit inputs and recalculate
  - click **Calculate funding** to visit https://traderepublic.com/de-de/altersvorsorgedepot

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
- `open_altersvorsorgedepot_calculator` (no arguments; opens the editable widget)
- `calculate_altersvorsorgedepot`
- `create_phone_signup_link` (legacy; not used by the widget)

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

The MCP server now provides an Apps SDK HTML widget at
`ui://widget/altersvorsorgedepot-v1.html`. Both calculator tools reference it via
`openai/outputTemplate`. The resource inlines its CSS and JavaScript; recalculation
uses `window.openai.callTool`, and the CTA uses `window.openai.openExternal`.
The same UI also works as a standalone FastAPI page.

1. Deploy the MCP service using `Dockerfile.mcp` or the included Render service.
   ChatGPT needs a reachable HTTPS MCP endpoint ending in `/mcp`, not localhost.
   The existing allowed host is `avd-calculator-mcp.onrender.com`; for a different
   deployment hostname, configure the transport's explicit allowed hosts/origins.
2. In a ChatGPT account with developer mode/custom app support, create a custom
   app pointing at that HTTPS `/mcp` endpoint, then connect/select it in a chat.
   Account availability and UI labels can vary.
3. Ask: “Show me an Altersvorsorgedepot calculator.” The no-argument
   `open_altersvorsorgedepot_calculator` tool displays editable example values.
   Use `chatgpt_instructions.md` if configuring an assistant's instructions.
4. Change assumptions and press **Potenzial berechnen** to recalculate in chat.
   **Calculate funding** opens the Trade Republic information page without
   passing phone numbers or calculator inputs.

An API Action alone does not render this widget. Adding the app does not make
it automatically appear in all chats for all users; public distribution requires
the applicable ChatGPT app publication/review process. This repository change
does not deploy the service or register/publish a ChatGPT app.

## Validation

```bash
.venv/bin/python -m unittest discover -s tests -v
```

These integration tests start the MCP server over stdio and verify tool discovery,
widget resource metadata, example hydration, calculator results, and the CTA URL.

## Compliance notes before going live

- Add legal review for subsidy assumptions and text
- Add GDPR-compliant consent logging for phone leads
- Add KYC/AML and suitability checks before account activation
- Avoid personalized regulated advice in assistant responses

