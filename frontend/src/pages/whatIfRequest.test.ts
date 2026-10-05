import { describe, expect, it } from "vitest";
import { buildHeroWhatIfRequest } from "./whatIfRequest";
import { CANONICAL_DEMO } from "../demo/config";

describe("buildHeroWhatIfRequest", () => {
  it("always sends the hero simulation ID as the explicit base_simulation_id", () => {
    const request = buildHeroWhatIfRequest("sim-aggressive01", "NORMAL_DRIVING");
    expect(request.base_simulation_id).toBe("sim-aggressive01");
  });

  it("uses the chosen counterfactual scenario and the locked canonical parameters", () => {
    const request = buildHeroWhatIfRequest("sim-aggressive01", "FAST_CHARGING");
    expect(request).toEqual({
      vehicle_id: CANONICAL_DEMO.vehicleId,
      counterfactual_scenario: "FAST_CHARGING",
      base_simulation_id: "sim-aggressive01",
      seed: CANONICAL_DEMO.seed,
      duration_minutes: CANONICAL_DEMO.durationMinutes,
      interval_seconds: CANONICAL_DEMO.intervalSeconds,
    });
  });
});
