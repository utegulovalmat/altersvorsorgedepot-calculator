# Altersvorsorgedepot calculator

Interactive retirement calculator for Germany's Altersvorsorgedepot. The same interface runs as a website and as one MCP Apps widget inside ChatGPT. Users can adjust their assumptions and open the verified Trade Republic website to register. The calculator does not collect phone numbers.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/`. The calculation endpoint is `POST /avd/calculate`; the API schema is at `/openapi.json`.

To run the MCP server:

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8001 python mcp_server.py
```

Its endpoint is `http://localhost:8001/mcp`. It exposes:

- `show_avd_calculator`: renders `ui://avd/calculator-v2.html` as one interactive ChatGPT iframe.
- `calculate_altersvorsorgedepot`: returns structured calculation data for changes inside that iframe or text-only clients.

The widget uses the MCP Apps bridge to call the calculation tool and opens `https://traderepublic.com/de-de` through ChatGPT's external-link API. On the standalone website it calls the same-origin REST endpoint and opens the link in a new tab.

Run the MCP widget integration test with `python -m unittest discover -s tests -v`.

## Deployment

`render.yaml` defines two Docker services. The public endpoints are:

- Website and API: `https://avd-calculator-api.onrender.com/`
- MCP: `https://avd-calculator-mcp.onrender.com/mcp`

Connect the MCP endpoint as a custom app in ChatGPT, then ask for an Altersvorsorgedepot or ETF retirement calculation. ChatGPT app availability and public distribution depend on the account's workspace permissions and OpenAI review. The installed private plugin created earlier is instructions-only until the MCP server is attached to it.

## Model assumptions

The code currently models up to €6,840 in annual contributions and €1,800 in subsidy-eligible contributions. The basic subsidy is 50% on the first €360 and 25% on the next €1,440, up to €540 per year. It also models up to €300 per eligible child each year and a one-time €200 starter bonus for savers under 25. Contributions and subsidy are invested at the assumed return after annual costs. The projection omits tax, inflation, changing child eligibility, and future rule changes. It is educational and should be reviewed against final rules before public marketing.
