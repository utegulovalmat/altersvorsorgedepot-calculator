const calculatorForm = document.querySelector("#calculator-form");
const errorSection = document.querySelector("#error");
const metricEndCapital = document.querySelector("#metric-end-capital");
const metricOwnContrib = document.querySelector("#metric-own-contrib");
const metricSubsidy = document.querySelector("#metric-subsidy");
const metricUplift = document.querySelector("#metric-uplift");
const disclaimer = document.querySelector("#disclaimer");

const toEuro = (value) =>
  new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);

let rpcId = 0;
let calculationId = 0;
let debounceTimer;
const pendingRequests = new Map();

const rpcNotify = (method, params) => {
  window.parent.postMessage({ jsonrpc: "2.0", method, params }, "*");
};

const rpcRequest = (method, params) =>
  new Promise((resolve, reject) => {
    const id = ++rpcId;
    pendingRequests.set(id, { resolve, reject });
    window.parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
  });

const getInputs = () => {
  const formData = new FormData(calculatorForm);
  return {
    current_age: Number(formData.get("current_age")),
    retirement_age: Number(formData.get("retirement_age")),
    monthly_contribution: Number(formData.get("monthly_contribution")),
    expected_annual_return_pct: Number(formData.get("expected_annual_return_pct")),
    annual_cost_pct: Number(formData.get("annual_cost_pct")),
    eligible_children: Number(formData.get("eligible_children")),
    include_starter_bonus: formData.has("include_starter_bonus"),
  };
};

const applyInputs = (inputs) => {
  if (!inputs || typeof inputs !== "object") return;
  for (const [name, value] of Object.entries(inputs)) {
    const control = calculatorForm.elements.namedItem(name);
    if (!control || value === undefined || value === null) continue;
    if (control.type === "checkbox") control.checked = Boolean(value);
    else control.value = String(value);
  }
};

const render = (data) => {
  if (!data || typeof data.projected_value !== "number") return;
  metricEndCapital.textContent = toEuro(data.projected_value);
  metricOwnContrib.textContent = toEuro(data.total_contributed);
  metricSubsidy.textContent = toEuro(data.total_government_subsidy);
  metricUplift.textContent = toEuro(data.subsidy_value_uplift);
  disclaimer.textContent = data.disclaimer;
  errorSection.textContent = "";
  errorSection.classList.add("hidden");
};

const showError = (message) => {
  errorSection.textContent = message;
  errorSection.classList.remove("hidden");
};

window.addEventListener("message", (event) => {
  if (event.source !== window.parent) return;
  const message = event.data;
  if (!message || message.jsonrpc !== "2.0") return;

  if (typeof message.id === "number" && pendingRequests.has(message.id)) {
    const pending = pendingRequests.get(message.id);
    pendingRequests.delete(message.id);
    if (message.error) pending.reject(message.error);
    else pending.resolve(message.result);
    return;
  }

  if (message.method === "ui/notifications/tool-input") applyInputs(message.params);
  if (message.method === "ui/notifications/tool-result") {
    applyInputs(message.params?.structuredContent?.inputs);
    render(message.params?.structuredContent);
  }
}, { passive: true });

const bridgeReady = window.parent === window
  ? Promise.resolve(false)
  : rpcRequest("ui/initialize", {
      appInfo: { name: "avd-calculator", version: "1.0.0" },
      appCapabilities: {},
      protocolVersion: "2026-01-26",
    }).then(() => {
      rpcNotify("ui/notifications/initialized", {});
      return true;
    });

const calculate = async () => {
  if (!calculatorForm.checkValidity()) {
    showError("Bitte prüfe die Eingaben.");
    return;
  }

  const payload = getInputs();
  if (payload.retirement_age <= payload.current_age) {
    showError("Das Rentenalter muss über deinem aktuellen Alter liegen.");
    return;
  }

  const currentCalculation = ++calculationId;
  try {
    let data;
    if (await bridgeReady) {
      const response = await rpcRequest("tools/call", {
        name: "calculate_altersvorsorgedepot",
        arguments: payload,
      });
      data = response?.structuredContent;
    } else {
      const response = await fetch("/avd/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Berechnung fehlgeschlagen.");
      data = await response.json();
    }

    if (!data || typeof data.projected_value !== "number") {
      throw new Error("Kein Ergebnis erhalten.");
    }
    if (currentCalculation === calculationId) render(data);
  } catch (error) {
    if (currentCalculation === calculationId) showError(error?.message || "Berechnung fehlgeschlagen.");
  }
};

calculatorForm.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(calculate, 250);
});
calculatorForm.addEventListener("submit", (event) => event.preventDefault());

document.querySelector("#register-link").addEventListener("click", async (event) => {
  if (!window.openai?.openExternal) return;
  event.preventDefault();
  try {
    await window.openai.openExternal({ href: event.currentTarget.href, redirectUrl: false });
  } catch (error) {
    showError("Der Link konnte nicht geöffnet werden. Bitte nutze traderepublic.com/de-de.");
  }
});

bridgeReady
  .then((ready) => {
    if (!ready) calculate();
  })
  .catch(() => showError("Der Rechner konnte nicht verbunden werden."));
