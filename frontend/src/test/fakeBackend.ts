// A stateful fake of the backend contract used by component and integration tests.
// It only implements endpoints the app calls, and it mirrors real ordering semantics.
import { vi } from "vitest";
import type { SimulationRunRequest, TelemetryItem } from "../api/types";
import {
  anomalyFixture,
  askCostNeedsPriceFixture,
  askCostWithPriceFixture,
  askResponseFixture,
  askUnknownFixture,
  askWhatIfFixture,
  contributorsFixture,
  costFixture,
  energyFixture,
  fastChargingWhatIfFixture,
  HERO_ID,
  NORMAL_ID,
  rangeFixture,
  recommendationsFixture,
  stressFixture,
  summaryFixture,
  vehicleFixture,
  VEHICLE_ID,
  whatIfFixture,
  whyFixture,
} from "./fixtures";

export class HttpStatus {
  constructor(readonly status: number) {}
}

export interface FakeCall {
  method: string;
  url: URL;
  body: unknown;
}

interface StoredSimulation {
  id: string;
  scenario: string;
  rows: TelemetryItem[];
}

export interface FakeWorld {
  calls: FakeCall[];
  simulations: StoredSimulation[];
  /** Simulated server-side scenario-lookup failure for a given simulation id. */
  failLookupFor: Set<string>;
  /** When true, every request fails at the network layer. */
  offline: boolean;
}

/** Deterministic IDs: the Nth created simulation gets a stable ID. */
function idFor(scenario: string, index: number): string {
  return `sim-${scenario.toLowerCase().slice(0, 6)}-${index}`;
}

export function createFakeWorld(initial: Array<{ scenario: string; startIso?: string }> = []): FakeWorld {
  const world: FakeWorld = { calls: [], simulations: [], failLookupFor: new Set(), offline: false };
  initial.forEach((item, i) => addSimulation(world, item.scenario, i, item.startIso));
  installFetch(world);
  return world;
}

function addSimulation(world: FakeWorld, scenario: string, index: number, startIso?: string): StoredSimulation {
  const id = scenario === "AGGRESSIVE_DRIVING" ? HERO_ID : scenario === "NORMAL_DRIVING" ? NORMAL_ID : idFor(scenario, index);
  const rows = syntheticRows(id, 180, startIso);
  const stored = { id, scenario, rows };
  world.simulations.push(stored);
  return stored;
}

function syntheticRows(simulationId: string, count: number, startIso?: string): TelemetryItem[] {
  const start = Date.parse(startIso ?? "2026-01-01T00:00:00Z");
  return Array.from({ length: count }, (_, i) => ({
    telemetry_id: i + 1,
    simulation_id: simulationId,
    vehicle_id: VEHICLE_ID,
    timestamp: new Date(start + i * 10_000).toISOString(),
    soc_percent: 80 - i * 0.02,
    battery_temperature_c: 30 + i * 0.01,
    speed_kmh: 60,
    battery_power_kw: 5,
    charging: false,
  }));
}

function installFetch(world: FakeWorld): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = new URL(input);
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      world.calls.push({ method, url, body });
      if (world.offline) throw new TypeError("Failed to fetch");
      try {
        const data = route(world, method, url, body);
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      } catch (err) {
        if (err instanceof HttpStatus) {
          return new Response(JSON.stringify({ detail: "server detail must not be shown" }), {
            status: err.status,
            headers: { "Content-Type": "application/json" },
          });
        }
        throw err;
      }
    }),
  );
}

function scenarioOf(world: FakeWorld, simulationId: string | null): string {
  const sim = world.simulations.find((s) => s.id === simulationId);
  if (!sim) throw new HttpStatus(404);
  return sim.scenario;
}

function route(world: FakeWorld, method: string, url: URL, body: unknown): unknown {
  const path = url.pathname;
  const simId = url.searchParams.get("simulation_id");

  if (method === "GET" && path === `/api/v1/vehicles/${VEHICLE_ID}/telemetry`) {
    const all = world.simulations.flatMap((s) => s.rows).sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
    const limit = Number(url.searchParams.get("limit") ?? 100);
    const offset = Number(url.searchParams.get("offset") ?? 0);
    const items = all.slice(offset, offset + limit);
    return { vehicle_id: VEHICLE_ID, count: items.length, limit, offset, items };
  }

  if (method === "POST" && path === "/api/v1/simulation/run") {
    const req = body as SimulationRunRequest;
    const index = world.simulations.length;
    const sim = addSimulation(world, req.scenario, index, req.simulation_start_time);
    return {
      simulation_id: sim.id,
      vehicle_id: VEHICLE_ID,
      scenario: req.scenario,
      mode: req.mode,
      seed: req.seed,
      start_time: req.simulation_start_time,
      duration_minutes: req.duration_minutes,
      interval_seconds: req.interval_seconds,
      samples_generated: sim.rows.length,
      starting_soc: 80,
      ending_soc: 78,
      energy_consumed: 3,
      distance: 50,
    };
  }

  if (method === "POST" && path === "/api/v1/simulation/reset") {
    const deleted = world.simulations.length;
    const telemetry = world.simulations.reduce((n, s) => n + s.rows.length, 0);
    world.simulations = [];
    return {
      vehicle_id: VEHICLE_ID,
      telemetry_deleted: telemetry,
      simulations_deleted: deleted,
      message: "reset",
    };
  }

  if (method === "GET" && path === `/api/v1/vehicles/${VEHICLE_ID}`) {
    return vehicleFixture();
  }

  if (path === "/api/v1/intelligence/what-if" && method === "POST") {
    const req = body as { base_simulation_id: string; counterfactual_scenario: string };
    scenarioOf(world, req.base_simulation_id); // throws 404 for unknown base simulations
    return req.counterfactual_scenario === "FAST_CHARGING"
      ? fastChargingWhatIfFixture()
      : whatIfFixture({ base_simulation_id: req.base_simulation_id });
  }

  if (path === "/api/v1/intelligence/cost" && method === "POST") {
    return costFixture();
  }

  if (path === "/api/v1/ai/ask" && method === "POST") {
    const req = body as { question: string; electricity_price_per_kwh?: number };
    const question = req.question.toLowerCase();
    if (/what if|normally/.test(question)) return askWhatIfFixture();
    if (/cost|spend|spent|price|pay/.test(question)) {
      return req.electricity_price_per_kwh ? askCostWithPriceFixture() : askCostNeedsPriceFixture();
    }
    if (/why|efficien|stress|anomal|unusual|should|worse|vehicle|energy/.test(question)) {
      return askResponseFixture();
    }
    return askUnknownFixture();
  }

  const intelligence = /^\/api\/v1\/intelligence\/([a-z-]+)\/[^/]+$/.exec(path);
  if (method === "GET" && intelligence) {
    const kind = intelligence[1];
    if (kind === "why-range-dropped") {
      if (simId && world.failLookupFor.has(simId)) throw new HttpStatus(500);
      const scenario = simId ? scenarioOf(world, simId) : "AGGRESSIVE_DRIVING";
      return whyFixture({ observed_simulation_id: simId ?? HERO_ID, observed_scenario: scenario });
    }
    if (simId && world.simulations.every((s) => s.id !== simId)) throw new HttpStatus(404);
    const isNormal = simId === NORMAL_ID;
    switch (kind) {
      case "summary":
        return summaryFixture();
      case "range":
        return rangeFixture(isNormal ? { estimated_range_km: 436.35, current_soc_percent: 75.22 } : {});
      case "energy":
        return energyFixture();
      case "anomaly":
        return anomalyFixture();
      case "battery-stress":
        return stressFixture();
      case "contributors":
        return contributorsFixture();
      case "recommendations":
        return recommendationsFixture(3);
      default:
        throw new HttpStatus(404);
    }
  }

  throw new HttpStatus(404);
}
