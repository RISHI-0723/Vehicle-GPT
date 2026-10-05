import { describe, expect, it } from "vitest";
import {
  canonicalRunRequest,
  DemoPreparationError,
  matchesCanonicalSignature,
  prepareCanonicalDemo,
  resolveCanonicalDemo,
  resetCanonicalDemo,
  type DemoPorts,
} from "./canonical";
import { CANONICAL_DEMO } from "./config";
import type { DriveRecord } from "./discovery";
import { createFakeWorld } from "../test/fakeBackend";

function drive(overrides: Partial<DriveRecord> = {}): DriveRecord {
  return {
    simulationId: "sim-x",
    scenario: "NORMAL_DRIVING",
    sampleCount: CANONICAL_DEMO.sampleCount,
    startTime: CANONICAL_DEMO.simulationStartTime,
    endTime: "2026-01-01T00:30:00Z",
    stepSeconds: CANONICAL_DEMO.intervalSeconds,
    durationMinutes: 30,
    endSocPercent: 78,
    endBatteryTemperatureC: 31,
    ...overrides,
  };
}

describe("matchesCanonicalSignature", () => {
  it("matches a drive with the exact canonical sample count, step and start time", () => {
    expect(matchesCanonicalSignature(drive())).toBe(true);
  });

  it("rejects a drive with a different sample count", () => {
    expect(matchesCanonicalSignature(drive({ sampleCount: 90 }))).toBe(false);
  });

  it("rejects a drive with a different step", () => {
    expect(matchesCanonicalSignature(drive({ stepSeconds: 5 }))).toBe(false);
  });

  it("rejects a drive with a different start time", () => {
    expect(matchesCanonicalSignature(drive({ startTime: "2026-02-01T00:00:00Z" }))).toBe(false);
  });

  it("matches a start time missing the UTC designator, as the real telemetry endpoint returns it", () => {
    // Regression test: /api/v1/vehicles/{id}/telemetry serializes `timestamp`
    // without a trailing "Z" (unlike simulation.start_time, which has one),
    // even though it is always UTC synthetic simulation time. A bare
    // Date.parse of an offset-less string is local-time per the ECMAScript
    // spec, which silently failed this check outside UTC+0 and made
    // "Prepare Demo" create duplicate simulations on every attempt.
    expect(matchesCanonicalSignature(drive({ startTime: "2026-01-01T00:00:00" }))).toBe(true);
  });

  it("still rejects a mismatched start time that is missing the UTC designator", () => {
    expect(matchesCanonicalSignature(drive({ startTime: "2026-02-01T00:00:00" }))).toBe(false);
  });
});

describe("resolveCanonicalDemo", () => {
  it("is not ready when neither canonical drive is present", () => {
    const resolution = resolveCanonicalDemo([]);
    expect(resolution.ready).toBe(false);
    expect(resolution.normal).toBeNull();
    expect(resolution.aggressive).toBeNull();
  });

  it("is ready once both canonical scenarios are present with matching signatures", () => {
    const drives = [
      drive({ simulationId: "sim-n", scenario: "NORMAL_DRIVING" }),
      drive({ simulationId: "sim-a", scenario: "AGGRESSIVE_DRIVING" }),
    ];
    const resolution = resolveCanonicalDemo(drives);
    expect(resolution.ready).toBe(true);
    expect(resolution.normal?.simulationId).toBe("sim-n");
    expect(resolution.aggressive?.simulationId).toBe("sim-a");
  });

  it("ignores drives whose signature does not match the canonical contract", () => {
    const drives = [drive({ simulationId: "sim-n", scenario: "NORMAL_DRIVING", sampleCount: 5 })];
    expect(resolveCanonicalDemo(drives).normal).toBeNull();
  });

  it("picks the lexicographically smallest simulation ID among duplicates, deterministically", () => {
    const drives = [
      drive({ simulationId: "sim-b", scenario: "NORMAL_DRIVING" }),
      drive({ simulationId: "sim-a", scenario: "NORMAL_DRIVING" }),
    ];
    expect(resolveCanonicalDemo(drives).normal?.simulationId).toBe("sim-a");
  });

  it("collects drives whose scenario could not be verified", () => {
    const unverified = drive({ simulationId: "sim-?", scenario: null });
    const resolution = resolveCanonicalDemo([unverified]);
    expect(resolution.unverified).toEqual([unverified]);
  });
});

describe("canonicalRunRequest", () => {
  it("builds a request with the locked canonical parameters for the given scenario", () => {
    const request = canonicalRunRequest("AGGRESSIVE_DRIVING");
    expect(request).toEqual({
      vehicle_id: CANONICAL_DEMO.vehicleId,
      scenario: "AGGRESSIVE_DRIVING",
      duration_minutes: CANONICAL_DEMO.durationMinutes,
      interval_seconds: CANONICAL_DEMO.intervalSeconds,
      seed: CANONICAL_DEMO.seed,
      mode: CANONICAL_DEMO.mode,
      simulation_start_time: CANONICAL_DEMO.simulationStartTime,
    });
  });
});

describe("prepareCanonicalDemo", () => {
  it("returns immediately without calling run when both drives already exist", async () => {
    const existing = [
      drive({ simulationId: "sim-n", scenario: "NORMAL_DRIVING" }),
      drive({ simulationId: "sim-a", scenario: "AGGRESSIVE_DRIVING" }),
    ];
    const run = async () => {
      throw new Error("run should not be called when already ready");
    };
    const ports: DemoPorts = { discover: async () => existing, run };
    const result = await prepareCanonicalDemo(ports);
    expect(result.normal.simulationId).toBe("sim-n");
    expect(result.aggressive.simulationId).toBe("sim-a");
  });

  it("refuses to create drives when an unverified simulation is present", async () => {
    const ports: DemoPorts = {
      discover: async () => [drive({ simulationId: "sim-?", scenario: null })],
      run: async () => {
        throw new Error("run should not be called when unverified data exists");
      },
    };
    await expect(prepareCanonicalDemo(ports)).rejects.toBeInstanceOf(DemoPreparationError);
  });

  it("creates only the missing drives, in canonical order, when starting from nothing", async () => {
    const created: string[] = [];
    let discoverCalls = 0;
    const ports: DemoPorts = {
      discover: async () => {
        discoverCalls += 1;
        if (discoverCalls === 1) return [];
        return [
          drive({ simulationId: "sim-n", scenario: "NORMAL_DRIVING" }),
          drive({ simulationId: "sim-a", scenario: "AGGRESSIVE_DRIVING" }),
        ];
      },
      run: async (request) => {
        created.push(request.scenario);
      },
    };
    const result = await prepareCanonicalDemo(ports);
    expect(created).toEqual(["NORMAL_DRIVING", "AGGRESSIVE_DRIVING"]);
    expect(result.normal.simulationId).toBe("sim-n");
    expect(result.aggressive.simulationId).toBe("sim-a");
  });

  it("creates only the one missing drive when the other already exists", async () => {
    const created: string[] = [];
    const ports: DemoPorts = {
      discover: async () => {
        if (created.length === 0) return [drive({ simulationId: "sim-n", scenario: "NORMAL_DRIVING" })];
        return [
          drive({ simulationId: "sim-n", scenario: "NORMAL_DRIVING" }),
          drive({ simulationId: "sim-a", scenario: "AGGRESSIVE_DRIVING" }),
        ];
      },
      run: async (request) => {
        created.push(request.scenario);
      },
    };
    await prepareCanonicalDemo(ports);
    expect(created).toEqual(["AGGRESSIVE_DRIVING"]);
  });

  it("throws when creation completes but verification still fails", async () => {
    const ports: DemoPorts = {
      discover: async () => [],
      run: async () => undefined,
    };
    await expect(prepareCanonicalDemo(ports)).rejects.toBeInstanceOf(DemoPreparationError);
  });
});

describe("resetCanonicalDemo", () => {
  it("calls the reset endpoint for the canonical demo vehicle", async () => {
    const world = createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const result = (await resetCanonicalDemo()) as { message: string; simulations_deleted: number };
    expect(result.message).toBe("reset");
    expect(result.simulations_deleted).toBe(2);
    const resetCall = world.calls.find((c) => c.url.pathname === "/api/v1/simulation/reset");
    expect(resetCall?.body).toEqual({ vehicle_id: CANONICAL_DEMO.vehicleId });
  });
});
