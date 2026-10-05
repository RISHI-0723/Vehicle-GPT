// Pure canonical-demo resolution and bootstrap logic (no React here).
import { backendApi } from "../api/endpoints";
import type { SimulationRunRequest } from "../api/types";
import { CANONICAL_DEMO, type CanonicalScenario } from "./config";
import type { DriveRecord } from "./discovery";

export interface CanonicalDemo {
  normal: DriveRecord;
  aggressive: DriveRecord;
}

export interface CanonicalResolution {
  normal: DriveRecord | null;
  aggressive: DriveRecord | null;
  ready: boolean;
  /** Drives whose scenario could not be verified. Their presence blocks creation. */
  unverified: DriveRecord[];
}

const CANONICAL_START_MS = Date.parse(CANONICAL_DEMO.simulationStartTime);

/**
 * The backend's telemetry timestamp field omits the UTC "Z" designator
 * (unlike e.g. simulation.start_time, which includes it), even though every
 * simulation timestamp is UTC synthetic simulation time. A bare
 * `Date.parse("2026-01-01T00:00:00")` (no offset) is interpreted as LOCAL
 * time per the ECMAScript spec, not UTC -- which silently made every drive
 * fail the canonical-signature check outside UTC+0 and caused "Prepare Demo"
 * to create duplicate simulations on every attempt. Treat an offset-less ISO
 * string as UTC explicitly instead of relying on the backend's (currently
 * inconsistent) serialization of this one field.
 */
function parseAsUtc(iso: string): number {
  const hasOffset = /Z$|[+-]\d{2}:\d{2}$/.test(iso);
  return Date.parse(hasOffset ? iso : `${iso}Z`);
}

/** True only for a drive matching the canonical parameters (sample count, step, start time). */
export function matchesCanonicalSignature(drive: DriveRecord): boolean {
  return (
    drive.sampleCount === CANONICAL_DEMO.sampleCount &&
    drive.stepSeconds === CANONICAL_DEMO.intervalSeconds &&
    parseAsUtc(drive.startTime) === CANONICAL_START_MS
  );
}

function pickCanonical(drives: DriveRecord[], scenario: CanonicalScenario): DriveRecord | null {
  // Identical parameters with the same seed yield identical telemetry, so when duplicates
  // exist any one of them is equivalent. Sorting by ID keeps the choice deterministic.
  const candidates = drives
    .filter((d) => d.scenario === scenario && matchesCanonicalSignature(d))
    .sort((a, b) => a.simulationId.localeCompare(b.simulationId));
  return candidates[0] ?? null;
}

export function resolveCanonicalDemo(drives: DriveRecord[]): CanonicalResolution {
  const normal = pickCanonical(drives, "NORMAL_DRIVING");
  const aggressive = pickCanonical(drives, "AGGRESSIVE_DRIVING");
  return {
    normal,
    aggressive,
    ready: normal !== null && aggressive !== null,
    unverified: drives.filter((d) => d.scenario === null),
  };
}

export function canonicalRunRequest(scenario: CanonicalScenario): SimulationRunRequest {
  return {
    vehicle_id: CANONICAL_DEMO.vehicleId,
    scenario,
    duration_minutes: CANONICAL_DEMO.durationMinutes,
    interval_seconds: CANONICAL_DEMO.intervalSeconds,
    seed: CANONICAL_DEMO.seed,
    mode: CANONICAL_DEMO.mode,
    simulation_start_time: CANONICAL_DEMO.simulationStartTime,
  };
}

export class DemoPreparationError extends Error {}

export interface DemoPorts {
  discover: () => Promise<DriveRecord[]>;
  run: (request: SimulationRunRequest) => Promise<unknown>;
}

/**
 * Creates ONLY the missing canonical drives, in canonical order.
 * Returns immediately (no writes) when both drives already exist, so refresh never duplicates.
 */
export async function prepareCanonicalDemo(ports: DemoPorts): Promise<CanonicalDemo> {
  const initial = resolveCanonicalDemo(await ports.discover());
  if (initial.ready) {
    return { normal: initial.normal!, aggressive: initial.aggressive! };
  }
  if (initial.unverified.length > 0) {
    // Creating here could duplicate a simulation whose scenario we could not confirm.
    throw new DemoPreparationError("Existing simulation data could not be verified. Try again.");
  }

  for (const scenario of CANONICAL_DEMO.sequence) {
    const alreadyPresent =
      (scenario === "NORMAL_DRIVING" && initial.normal !== null) ||
      (scenario === "AGGRESSIVE_DRIVING" && initial.aggressive !== null);
    if (alreadyPresent) continue;
    // Sequential awaits: NORMAL_DRIVING is persisted before AGGRESSIVE_DRIVING is requested.
    await ports.run(canonicalRunRequest(scenario));
  }

  const verified = resolveCanonicalDemo(await ports.discover());
  if (!verified.ready) {
    throw new DemoPreparationError("Demo data was created but could not be verified. Try again.");
  }
  return { normal: verified.normal!, aggressive: verified.aggressive! };
}

export function resetCanonicalDemo(): Promise<unknown> {
  return backendApi.resetVehicle(CANONICAL_DEMO.vehicleId);
}
