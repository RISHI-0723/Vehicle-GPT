// One function per backend endpoint used by the app. Paths and bodies match the
// implemented routes exactly (see SPRINT_2_REPORT.md section 14).
import { requestJson, withQuery } from "./client";
import type {
  AnomalyDetection,
  AskRequest,
  AskResponse,
  BatteryStress,
  ContributorAnalysis,
  CostRequest,
  CostResponse,
  EnergyAnalysis,
  IntelligenceSummary,
  RangeEstimation,
  Recommendations,
  ResetResponse,
  SimulationRunRequest,
  SimulationRunResponse,
  TelemetryPage,
  VehicleInfo,
  WhatIfRequest,
  WhatIfResponse,
  WhyRangeDropped,
} from "./types";

const INTEL = "/api/v1/intelligence";

function intelligencePath(kind: string, vehicleId: string, simulationId?: string): string {
  return withQuery(`${INTEL}/${kind}/${encodeURIComponent(vehicleId)}`, {
    simulation_id: simulationId,
  });
}

export const intelligenceApi = {
  energy: (vehicleId: string, simulationId?: string) =>
    requestJson<EnergyAnalysis>(intelligencePath("energy", vehicleId, simulationId)),
  range: (vehicleId: string, simulationId?: string) =>
    requestJson<RangeEstimation>(intelligencePath("range", vehicleId, simulationId)),
  anomaly: (vehicleId: string, simulationId?: string) =>
    requestJson<AnomalyDetection>(intelligencePath("anomaly", vehicleId, simulationId)),
  batteryStress: (vehicleId: string, simulationId?: string) =>
    requestJson<BatteryStress>(intelligencePath("battery-stress", vehicleId, simulationId)),
  contributors: (vehicleId: string, simulationId?: string) =>
    requestJson<ContributorAnalysis>(intelligencePath("contributors", vehicleId, simulationId)),
  recommendations: (vehicleId: string, simulationId?: string) =>
    requestJson<Recommendations>(intelligencePath("recommendations", vehicleId, simulationId)),
  whyRangeDropped: (vehicleId: string, simulationId?: string) =>
    requestJson<WhyRangeDropped>(intelligencePath("why-range-dropped", vehicleId, simulationId)),
  summary: (vehicleId: string, simulationId?: string) =>
    requestJson<IntelligenceSummary>(intelligencePath("summary", vehicleId, simulationId)),
  whatIf: (body: WhatIfRequest) =>
    requestJson<WhatIfResponse>(`${INTEL}/what-if`, { method: "POST", body }),
  cost: (body: CostRequest) =>
    requestJson<CostResponse>(`${INTEL}/cost`, { method: "POST", body }),
};

export const backendApi = {
  vehicle: (vehicleId: string) =>
    requestJson<VehicleInfo>(`/api/v1/vehicles/${encodeURIComponent(vehicleId)}`),
  telemetryPage: (vehicleId: string, limit: number, offset: number) =>
    requestJson<TelemetryPage>(
      withQuery(`/api/v1/vehicles/${encodeURIComponent(vehicleId)}/telemetry`, { limit, offset }),
    ),
  runSimulation: (body: SimulationRunRequest) =>
    requestJson<SimulationRunResponse>("/api/v1/simulation/run", { method: "POST", body }),
  resetVehicle: (vehicleId: string) =>
    requestJson<ResetResponse>("/api/v1/simulation/reset", {
      method: "POST",
      body: { vehicle_id: vehicleId },
    }),
};

export const aiApi = {
  ask: (body: AskRequest) => requestJson<AskResponse>("/api/v1/ai/ask", { method: "POST", body }),
};
