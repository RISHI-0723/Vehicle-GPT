import { describe, expect, it } from "vitest";
import { discoverDrives, fetchAllTelemetry, groupTelemetry, summarizeDrive } from "./discovery";
import type { TelemetryItem } from "../api/types";
import { createFakeWorld } from "../test/fakeBackend";
import { HERO_ID, NORMAL_ID, VEHICLE_ID } from "../test/fixtures";

function row(overrides: Partial<TelemetryItem> = {}): TelemetryItem {
  return {
    telemetry_id: 1,
    simulation_id: "sim-1",
    vehicle_id: VEHICLE_ID,
    timestamp: "2026-01-01T00:00:00Z",
    soc_percent: 80,
    battery_temperature_c: 30,
    speed_kmh: 60,
    battery_power_kw: 5,
    charging: false,
    ...overrides,
  };
}

describe("groupTelemetry", () => {
  it("groups rows by simulation_id, preserving row order within a group", () => {
    const rows = [
      row({ telemetry_id: 1, simulation_id: "a" }),
      row({ telemetry_id: 2, simulation_id: "b" }),
      row({ telemetry_id: 3, simulation_id: "a" }),
    ];
    const groups = groupTelemetry(rows);
    expect([...groups.keys()].sort()).toEqual(["a", "b"]);
    expect(groups.get("a")?.map((r) => r.telemetry_id)).toEqual([1, 3]);
  });

  it("returns an empty map for no rows", () => {
    expect(groupTelemetry([]).size).toBe(0);
  });
});

describe("summarizeDrive", () => {
  it("derives step seconds and duration from the sorted timestamps", () => {
    const rows = [
      row({ timestamp: "2026-01-01T00:00:10Z", soc_percent: 79, battery_temperature_c: 30.1 }),
      row({ timestamp: "2026-01-01T00:00:00Z", soc_percent: 80, battery_temperature_c: 30 }),
      row({ timestamp: "2026-01-01T00:00:20Z", soc_percent: 78, battery_temperature_c: 30.2 }),
    ];
    const summary = summarizeDrive("sim-1", rows, "NORMAL_DRIVING");
    expect(summary.simulationId).toBe("sim-1");
    expect(summary.scenario).toBe("NORMAL_DRIVING");
    expect(summary.sampleCount).toBe(3);
    expect(summary.startTime).toBe("2026-01-01T00:00:00Z");
    expect(summary.endTime).toBe("2026-01-01T00:00:20Z");
    expect(summary.stepSeconds).toBe(10);
    // (20s span + 10s step) / 60 = 0.5 min
    expect(summary.durationMinutes).toBeCloseTo(0.5);
    expect(summary.endSocPercent).toBe(78);
    expect(summary.endBatteryTemperatureC).toBe(30.2);
  });

  it("leaves step and duration null for a single-sample drive", () => {
    const summary = summarizeDrive("sim-1", [row()], null);
    expect(summary.stepSeconds).toBeNull();
    expect(summary.durationMinutes).toBeNull();
    expect(summary.scenario).toBeNull();
  });
});

describe("fetchAllTelemetry", () => {
  it("pages through telemetry until a short page signals the end", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }]); // 180 synthetic rows
    const all = await fetchAllTelemetry(VEHICLE_ID);
    expect(all).toHaveLength(180);
  });
});

describe("discoverDrives", () => {
  it("reports every persisted simulation with its backend-confirmed scenario", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const drives = await discoverDrives(VEHICLE_ID);
    const byId = new Map(drives.map((d) => [d.simulationId, d]));
    expect(byId.get(NORMAL_ID)?.scenario).toBe("NORMAL_DRIVING");
    expect(byId.get(HERO_ID)?.scenario).toBe("AGGRESSIVE_DRIVING");
  });

  it("reports scenario null, never a guess, when the scenario lookup fails", async () => {
    const world = createFakeWorld([{ scenario: "NORMAL_DRIVING" }]);
    world.failLookupFor.add(NORMAL_ID);
    const drives = await discoverDrives(VEHICLE_ID);
    expect(drives.find((d) => d.simulationId === NORMAL_ID)?.scenario).toBeNull();
  });

  it("returns an empty list when nothing is persisted", async () => {
    createFakeWorld([]);
    expect(await discoverDrives(VEHICLE_ID)).toEqual([]);
  });
});
