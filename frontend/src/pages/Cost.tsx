import { useId, useState, type FormEvent } from "react";
import { intelligenceApi } from "../api/endpoints";
import { toApiError } from "../api/client";
import type { CostResponse } from "../api/types";
import { Card, ErrorState, SectionHeading } from "../components/ui";
import { formatInr, formatKwh } from "../lib/format";
import { describeApiError } from "../lib/errors";
import { DEMO_VEHICLE_ID } from "../demo/config";
import type { CanonicalDemo } from "../demo/canonical";

type Phase =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "done"; result: CostResponse }
  | { kind: "error"; message: string };

const PRICE_REQUIRED = "Enter an electricity price in ₹ per kWh to calculate cost.";
const PRICE_POSITIVE = "Electricity price must be greater than zero.";

/** Returns the parsed price, or an error message. Nothing is ever defaulted. */
export function parseElectricityPrice(raw: string): { value: number } | { error: string } {
  const trimmed = raw.trim();
  if (trimmed === "") return { error: PRICE_REQUIRED };
  const value = Number(trimmed);
  if (!Number.isFinite(value)) return { error: PRICE_REQUIRED };
  if (value <= 0) return { error: PRICE_POSITIVE };
  return { value };
}

export function Cost({ hero }: { hero: CanonicalDemo }) {
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const [raw, setRaw] = useState("");
  const [validation, setValidation] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  async function calculate(event: FormEvent) {
    event.preventDefault();
    const parsed = parseElectricityPrice(raw);
    if ("error" in parsed) {
      setValidation(parsed.error);
      setPhase({ kind: "idle" });
      return;
    }
    setValidation(null);
    setPhase({ kind: "pending" });
    try {
      const result = await intelligenceApi.cost({
        vehicle_id: DEMO_VEHICLE_ID,
        simulation_id: hero.aggressive.simulationId,
        electricity_price_per_kwh: parsed.value,
      });
      setPhase({ kind: "done", result });
    } catch (err) {
      const apiError = toApiError(err);
      const priceRejected = apiError.kind === "http" && (apiError.status === 400 || apiError.status === 422);
      setPhase({
        kind: "error",
        message: priceRejected ? PRICE_POSITIVE : describeApiError(apiError),
      });
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">Trip cost</h1>
      <p className="muted">Uses this drive's energy and the electricity price you enter.</p>

      <form className="card" onSubmit={calculate} noValidate>
        <label htmlFor={inputId} className="field-label">
          Electricity price (₹ per kWh)
        </label>
        <input
          id={inputId}
          className="field"
          type="number"
          inputMode="decimal"
          min="0"
          step="0.01"
          placeholder="Enter price"
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          aria-invalid={validation !== null}
          aria-describedby={validation ? errorId : undefined}
        />
        {validation ? (
          <p id={errorId} className="field-error" role="alert">
            {validation}
          </p>
        ) : null}
        <button type="submit" className="btn btn--primary btn--block" disabled={phase.kind === "pending"}>
          {phase.kind === "pending" ? "Calculating…" : "Calculate trip cost"}
        </button>
      </form>

      {phase.kind === "error" ? <ErrorState message={phase.message} /> : null}

      {phase.kind === "done" ? <CostResult result={phase.result} /> : null}
    </div>
  );
}

function CostResult({ result }: { result: CostResponse }) {
  return (
    <Card labelledBy="cost-result" className="cost-result">
      <SectionHeading id="cost-result">Estimated cost</SectionHeading>
      <div className="metric-grid">
        <div className="metric">
          <span className="metric__label">Energy cost</span>
          <span className="metric__value">{formatInr(result.energy_cost_inr)}</span>
          <span className="metric__hint">{formatKwh(result.energy_used_kwh)} net energy</span>
        </div>
        <div className="metric">
          <span className="metric__label">Prototype wear proxy</span>
          <span className="metric__value">{formatInr(result.estimated_battery_wear_cost_inr)}</span>
          <span className="metric__hint">Not a measure of battery degradation</span>
        </div>
      </div>
      <p className="potential">
        Estimated operating cost: <strong>{formatInr(result.total_operating_cost_inr)}</strong>
      </p>
      {result.cost_per_km_inr !== null ? (
        <p className="muted small">{formatInr(result.cost_per_km_inr)} per km</p>
      ) : null}
      <p className="muted small">{result.disclaimer}</p>
    </Card>
  );
}
