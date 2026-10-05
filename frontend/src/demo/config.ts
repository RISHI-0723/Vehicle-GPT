// Canonical deterministic demo contract. Values are locked by the Sprint 3 spec.
// The backend simulator remains the source of truth for every resulting value.

export const DEMO_VEHICLE_ID = "VG-DEMO-001";

export const CANONICAL_DEMO = {
  vehicleId: DEMO_VEHICLE_ID,
  seed: 42,
  durationMinutes: 30,
  intervalSeconds: 10,
  mode: "fresh" as const,
  simulationStartTime: "2026-01-01T00:00:00Z",
  /** Order is part of the contract: NORMAL_DRIVING is always created first. */
  sequence: ["NORMAL_DRIVING", "AGGRESSIVE_DRIVING"] as const,
  /** Telemetry samples in one canonical drive: 30 min / 10 s. */
  sampleCount: 180,
  /** Counterfactual scenario for the hero what-if. */
  whatIfScenario: "NORMAL_DRIVING",
} as const;

export type CanonicalScenario = (typeof CANONICAL_DEMO.sequence)[number];

export const SCENARIO_LABELS: Record<string, string> = {
  NORMAL_DRIVING: "Normal Drive",
  AGGRESSIVE_DRIVING: "Aggressive Drive",
  HOT_INDIAN_DAY: "Hot Day Drive",
  ENERGY_ANOMALY: "Energy Anomaly Drive",
  FAST_CHARGING: "Simulated Charging",
};
