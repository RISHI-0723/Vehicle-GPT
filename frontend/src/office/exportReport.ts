// Builds the "Export Drive Report" Markdown file. Required sections per the
// Sprint 4 spec: Vehicle, Simulation, Energy, Range, Intelligence,
// Contributors, Recommendations, Disclosure. No secrets, no raw JSON.
import type { DriveRecord } from "../demo/discovery";
import type { VehicleInfo, WhyRangeDropped } from "../api/types";
import { formatKm, formatKwh, formatMinutes, formatPercent, impactCopy, scenarioLabel } from "../lib/format";

export function buildDriveReportMarkdown(params: {
  vehicle: VehicleInfo;
  drive: DriveRecord;
  summary: WhyRangeDropped;
}): string {
  const { vehicle, drive, summary } = params;
  const lines: string[] = [];

  lines.push("# VehicleGPT Drive Report", "");

  lines.push("## Vehicle");
  lines.push(`Vehicle ID: ${vehicle.vehicle_id}`);
  lines.push(`Vehicle name: ${vehicle.make} ${vehicle.model}`, "");

  lines.push("## Simulation");
  lines.push(`Simulation ID: ${drive.simulationId}`);
  lines.push(`Scenario: ${scenarioLabel(drive.scenario)}`);
  lines.push(`Start time: ${drive.startTime}`);
  lines.push(`Duration: ${formatMinutes(drive.durationMinutes)}`, "");

  lines.push("## Energy");
  lines.push(`Energy consumed: ${formatKwh(summary.energy.energy_consumed_kwh)}`);
  lines.push(`Energy regenerated: ${formatKwh(summary.energy.energy_regenerated_kwh)}`);
  lines.push(`Net energy: ${formatKwh(summary.energy.net_energy_kwh)}`);
  lines.push(`Efficiency: ${summary.energy.rating}`, "");

  lines.push("## Range");
  lines.push(
    `Estimated range: ${summary.range_estimate.estimated_range_km !== null ? formatKm(summary.range_estimate.estimated_range_km) : "Unavailable"}`,
  );
  lines.push(`Confidence: ${summary.range_estimate.confidence}`, "");

  lines.push("## Intelligence");
  lines.push(`Anomaly score: ${summary.anomaly.anomaly_score}`);
  lines.push(`Battery stress: ${summary.battery_stress.stress_level}`);
  lines.push(`Temperature exposure: ${formatPercent(summary.battery_stress.high_temperature_exposure_percent)}`, "");

  lines.push("## Contributors");
  const topContributors = summary.contributors.contributors.slice(0, 3);
  if (topContributors.length === 0) {
    lines.push("No contributor data is available for this drive.");
  } else {
    for (const c of topContributors) {
      lines.push(`- ${c.name}: ${c.is_available ? impactCopy(c.impact_level) : "No baseline comparison"}`);
    }
  }
  lines.push("");

  lines.push("## Recommendations");
  const recs = summary.recommendations.recommendations.slice(0, 5);
  if (recs.length === 0) {
    lines.push("No recommendations for this drive.");
  } else {
    for (const r of recs) {
      lines.push(`- [${r.priority}] ${r.title}: ${r.reason}`);
    }
  }
  lines.push("");

  lines.push("## Disclosure", "");
  lines.push("Synthetic simulated telemetry — not live vehicle data.", "");
  lines.push("Counterfactual results are simulations, not predictions.");

  return lines.join("\n");
}

export function driveReportFilename(drive: DriveRecord): string {
  return `vehiclegpt-drive-report-${drive.simulationId}.md`;
}
