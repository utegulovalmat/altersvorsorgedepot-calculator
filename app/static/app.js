const calculatorForm = document.querySelector("#calculator-form");

const resultsSection = document.querySelector("#results");
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

const clearError = () => {
  errorSection.textContent = "";
  errorSection.classList.add("hidden");
};

const showError = (message) => {
  errorSection.textContent = message;
  errorSection.classList.remove("hidden");
};

calculatorForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const formData = new FormData(calculatorForm);
  const payload = {
    current_age: Number(formData.get("current_age")),
    retirement_age: Number(formData.get("retirement_age")),
    monthly_contribution: Number(formData.get("monthly_contribution")),
    expected_annual_return_pct: Number(formData.get("expected_annual_return_pct")),
    annual_cost_pct: Number(formData.get("annual_cost_pct")),
    eligible_children: Number(formData.get("eligible_children")),
    include_starter_bonus: Boolean(formData.get("include_starter_bonus")),
  };

  const submitButton = calculatorForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = "Wird berechnet …";
  try {
    let data;
    if (window.openai?.callTool) {
      const response = await window.openai.callTool("calculate_altersvorsorgedepot", payload);
      if (response.isError) throw new Error("Berechnung fehlgeschlagen");
      data = response.structuredContent;
      if (!data) throw new Error("Keine Berechnung empfangen");
    } else {
      const response = await fetch("/avd/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const detail = await response.json();
        throw new Error(typeof detail.detail === "string" ? detail.detail : "Bitte prüfe deine Eingaben.");
      }
      data = await response.json();
    }
    renderResults(data);
  } catch (error) {
    showError(error.message || "Unbekannter Fehler");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Potenzial berechnen";
  }
});

function renderResults(data) {
  metricEndCapital.textContent = toEuro(data.projected_value);
  metricOwnContrib.textContent = toEuro(data.total_contributed);
  metricSubsidy.textContent = toEuro(data.total_government_subsidy);
  metricUplift.textContent = toEuro(data.subsidy_value_uplift);
  disclaimer.textContent = data.disclaimer;
  resultsSection.classList.remove("hidden");
  window.openai?.notifyIntrinsicHeight?.(document.documentElement.scrollHeight);
}

function hydrateWidget() {
  const data = window.openai?.toolOutput;
  if (!data?.yearly_projection) return;
  for (const [name, value] of Object.entries(data.inputs || {})) {
    const input = calculatorForm.elements.namedItem(name);
    if (!input) continue;
    if (input.type === "checkbox") input.checked = Boolean(value);
    else input.value = value;
  }
  renderResults(data);
}

window.addEventListener("openai:set_globals", hydrateWidget);
hydrateWidget();

document.querySelector("#funding-link").addEventListener("click", (event) => {
  if (window.openai?.openExternal) {
    event.preventDefault();
    window.openai.openExternal({ href: event.currentTarget.href });
  }
});
