// Human-readable clipboard text for "Copy Insight" / "Copy Simulation Result".
// Never copies raw JSON -- every field here is formatted prose.
import type { Contributor, Recommendation, WhatIfResponse } from "../api/types";
import { formatKm, formatKwh, formatSignedKm, impactCopy } from "../lib/format";

export function formatRangeInsight(params: {
  estimatedRangeKm: number | null;
  contributors: Contributor[];
  topRecommendation: Recommendation | null;
}): string {
  const lines: string[] = ["VehicleGPT — Range Analysis", ""];
  lines.push("Estimated range:");
  lines.push(params.estimatedRangeKm !== null ? formatKm(params.estimatedRangeKm) : "Unavailable");
  lines.push("");
  lines.push("Main contributors:");
  const top = params.contributors.slice(0, 3);
  if (top.length === 0) {
    lines.push("• No contributor data is available for this drive.");
  } else {
    for (const c of top) {
      lines.push(`• ${c.name}: ${c.is_available ? impactCopy(c.impact_level) : "No baseline comparison"}`);
    }
  }
  lines.push("");
  lines.push("Recommendation:");
  lines.push(
    params.topRecommendation
      ? `${params.topRecommendation.title}. ${params.topRecommendation.reason}`
      : "No recommendation available for this drive.",
  );
  lines.push("");
  lines.push("Source:");
  lines.push("Synthetic simulated telemetry");
  return lines.join("\n");
}

export function formatWhatIfInsight(result: WhatIfResponse): string {
  const lines: string[] = ["VehicleGPT — Simulation Result", ""];
  lines.push("Base:");
  lines.push(result.base_scenario);
  lines.push("");
  lines.push("Counterfactual:");
  lines.push(result.counterfactual_scenario);
  lines.push("");
  lines.push("Baseline energy use:");
  lines.push(`${formatKwh(result.base_metrics.energy_consumed_kwh)} over ${result.base_metrics.distance_km.toFixed(1)} km`);
  lines.push("");
  lines.push("Counterfactual energy use:");
  lines.push(
    `${formatKwh(result.counterfactual_metrics.energy_consumed_kwh)} over ${result.counterfactual_metrics.distance_km.toFixed(1)} km`,
  );
  lines.push("");
  lines.push("Estimated range difference:");
  lines.push(
    result.estimated_range_change_km !== null
      ? formatSignedKm(result.estimated_range_change_km)
      : "Not applicable (charging scenario)",
  );
  lines.push("");
  lines.push("This is a deterministic counterfactual simulation, not a prediction.");
  return lines.join("\n");
}
