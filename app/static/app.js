const calculatorForm = document.querySelector("#calculator-form");
const signupForm = document.querySelector("#signup-form");

const resultsSection = document.querySelector("#results");
const signupSection = document.querySelector("#signup");
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

  try {
    const response = await fetch("/avd/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const detail = await response.json();
      throw new Error(detail.detail || "Berechnung fehlgeschlagen");
    }

    const data = await response.json();
    metricEndCapital.textContent = toEuro(data.projected_value);
    metricOwnContrib.textContent = toEuro(data.total_contributed);
    metricSubsidy.textContent = toEuro(data.total_government_subsidy);
    metricUplift.textContent = toEuro(data.subsidy_value_uplift);
    disclaimer.textContent = data.disclaimer;

    resultsSection.classList.remove("hidden");
    signupSection.classList.remove("hidden");
  } catch (error) {
    showError(error.message || "Unbekannter Fehler");
  }
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const formData = new FormData(signupForm);
  const payload = {
    phone_number: String(formData.get("phone_number") || "").trim(),
    consent: Boolean(formData.get("consent")),
    source: "avd-calculator-web",
  };

  try {
    const response = await fetch("/signup/phone", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const detail = await response.json();
      throw new Error(detail.detail || "Signup konnte nicht gestartet werden");
    }

    const data = await response.json();
    window.location.href = data.signup_url;
  } catch (error) {
    showError(error.message || "Unbekannter Fehler");
  }
});
