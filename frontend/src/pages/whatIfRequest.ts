import type { WhatIfRequest } from "../api/types";
import { CANONICAL_DEMO } from "../demo/config";

export type WhatIfChoice = "NORMAL_DRIVING" | "FAST_CHARGING";

/**
 * Builds the what-if request for the hero drive. The AGGRESSIVE_DRIVING simulation ID is always
 * sent explicitly as base_simulation_id. The backend stays responsible for starting-state logic.
 */
export function buildHeroWhatIfRequest(heroSimulationId: string, scenario: WhatIfChoice): WhatIfRequest {
  return {
    vehicle_id: CANONICAL_DEMO.vehicleId,
    counterfactual_scenario: scenario,
    base_simulation_id: heroSimulationId,
    seed: CANONICAL_DEMO.seed,
    duration_minutes: CANONICAL_DEMO.durationMinutes,
    interval_seconds: CANONICAL_DEMO.intervalSeconds,
  };
}
