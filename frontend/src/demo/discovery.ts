// Discovers persisted simulations using EXISTING endpoints only.
//
// The backend exposes no simulation-list endpoint. Telemetry rows carry
// simulation_id, and the scenario of any simulation is reported by the
// why-range endpoint's observed_scenario. Both calls are read-only.
import { backendApi, intelligenceApi } from "../api/endpoints";
import type { TelemetryItem } from "../api/types";

export interface DriveRecord {
  simulationId: string;
  /** Scenario reported by the backend, or null if it could not be determined. */
  scenario: string | null;
  sampleCount: number;
  startTime: string;
  endTime: string;
  /** Step between samples, derived from persisted timestamps. */
  stepSeconds: number | null;
  /** Span covered by telemetry, including the final step. */
  durationMinutes: number | null;
  endSocPercent: number | null;
  endBatteryTemperatureC: number | null;
}

const PAGE_SIZE = 1000;
const MAX_PAGES = 100;

export async function fetchAllTelemetry(vehicleId: string): Promise<TelemetryItem[]> {
  const items: TelemetryItem[] = [];
  for (let page = 0; page < MAX_PAGES; page++) {
    const result = await backendApi.telemetryPage(vehicleId, PAGE_SIZE, page * PAGE_SIZE);
    items.push(...result.items);
    if (result.items.length < PAGE_SIZE) break;
  }
  return items;
}

export function groupTelemetry(items: TelemetryItem[]): Map<string, TelemetryItem[]> {
  const groups = new Map<string, TelemetryItem[]>();
  for (const item of items) {
    const list = groups.get(item.simulation_id);
    if (list) list.push(item);
    else groups.set(item.simulation_id, [item]);
  }
  return groups;
}

export function summarizeDrive(
  simulationId: string,
  rows: TelemetryItem[],
  scenario: string | null,
): DriveRecord {
  const sorted = [...rows].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const secondTs = sorted.length > 1 ? Date.parse(sorted[1].timestamp) : null;
  const firstTs = Date.parse(first.timestamp);
  const stepSeconds = secondTs !== null ? (secondTs - firstTs) / 1000 : null;
  const durationMinutes =
    stepSeconds !== null && stepSeconds > 0
      ? ((Date.parse(last.timestamp) - firstTs) / 1000 + stepSeconds) / 60
      : null;

  return {
    simulationId,
    scenario,
    sampleCount: rows.length,
    startTime: first.timestamp,
    endTime: last.timestamp,
    stepSeconds,
    durationMinutes,
    endSocPercent: last.soc_percent,
    endBatteryTemperatureC: last.battery_temperature_c,
  };
}

/**
 * Lists every persisted simulation for the vehicle with its backend-reported scenario.
 * A failed scenario lookup yields scenario = null (never a guessed value).
 */
export async function discoverDrives(vehicleId: string): Promise<DriveRecord[]> {
  const groups = groupTelemetry(await fetchAllTelemetry(vehicleId));
  const ids = [...groups.keys()].sort();

  return Promise.all(
    ids.map(async (simulationId) => {
      let scenario: string | null;
      try {
        const why = await intelligenceApi.whyRangeDropped(vehicleId, simulationId);
        scenario = why.observed_scenario;
      } catch {
        scenario = null;
      }
      return summarizeDrive(simulationId, groups.get(simulationId) ?? [], scenario);
    }),
  );
}
