// Display helpers. These format backend values and provide fixed UX copy only.
// No intelligence formulas live here.
import type { BaselineMatchType, ConfidenceLevel, StressLevel, ImpactLevel } from "../api/types";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

export function formatKm(value: number): string {
  return `${Math.round(value)} km`;
}

export function formatSignedKm(value: number): string {
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded} km`;
}

export function formatKwh(value: number): string {
  return `${value.toFixed(2)} kWh`;
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function formatInr(value: number): string {
  return inr.format(value);
}

export function formatMinutes(value: number | null): string {
  if (value === null) return "Duration unavailable";
  return `${Math.round(value)} min`;
}

export function scenarioLabel(scenario: string | null): string {
  switch (scenario) {
    case "NORMAL_DRIVING":
      return "Normal Drive";
    case "AGGRESSIVE_DRIVING":
      return "Aggressive Drive";
    case "HOT_INDIAN_DAY":
      return "Hot Day Drive";
    case "ENERGY_ANOMALY":
      return "Energy Anomaly Drive";
    case "FAST_CHARGING":
      return "Simulated Charging";
    default:
      return "Unidentified Drive";
  }
}

/** Baseline wording. APPROXIMATE is never presented as EXACT. */
export function baselineCopy(match: BaselineMatchType): string {
  switch (match) {
    case "EXACT":
      return "Compared with a matching normal drive.";
    case "APPROXIMATE":
      return "Compared with your closest recent normal drive.";
    case "UNAVAILABLE":
      return "Not enough comparable driving data yet.";
  }
}

/** Limited confidence is flagged; HIGH needs no extra copy. */
export function confidenceCopy(level: ConfidenceLevel): string | null {
  return level === "HIGH" ? null : "Limited comparison data.";
}

export function stressCopy(level: StressLevel): string {
  switch (level) {
    case "LOW":
      return "Low";
    case "MODERATE":
      return "Moderate";
    case "ELEVATED":
      return "Elevated";
    case "HIGH":
      return "High";
    case "CRITICAL":
      return "Critical";
  }
}

export function impactCopy(level: ImpactLevel): string {
  return level === "UNAVAILABLE" ? "No baseline comparison" : `${level} IMPACT`;
}

/** Anomaly language uses the backend's is_anomalous flag, never a diagnosis. */
export function anomalyCopy(isAnomalous: boolean): string {
  return isAnomalous
    ? "Your energy use is higher than expected."
    : "Your recent drive looks normal.";
}
