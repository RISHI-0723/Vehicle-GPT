import { describe, expect, it } from "vitest";
import { formatRangeInsight, formatWhatIfInsight } from "./insights";
import { contributorsFixture, recommendationFixtures, whatIfFixture } from "../test/fixtures";

describe("formatRangeInsight", () => {
  it("produces human-readable prose, never raw JSON", () => {
    const text = formatRangeInsight({
      estimatedRangeKm: 142,
      contributors: contributorsFixture().contributors,
      topRecommendation: recommendationFixtures(1)[0],
    });
    expect(text).not.toContain("{");
    expect(text).not.toContain("}");
    expect(text).toContain("VehicleGPT — Range Analysis");
    expect(text).toContain("142 km");
  });

  it("includes the required sections: estimate, contributors, recommendation, source", () => {
    const text = formatRangeInsight({
      estimatedRangeKm: 142,
      contributors: contributorsFixture().contributors,
      topRecommendation: recommendationFixtures(1)[0],
    });
    expect(text).toContain("Estimated range:");
    expect(text).toContain("Main contributors:");
    expect(text).toContain("Recommendation:");
    expect(text).toContain("Source:");
    expect(text).toContain("Synthetic simulated telemetry");
  });

  it("marks range as unavailable rather than inventing a number", () => {
    const text = formatRangeInsight({ estimatedRangeKm: null, contributors: [], topRecommendation: null });
    expect(text).toContain("Unavailable");
  });

  it("never fabricates a recommendation when none exists", () => {
    const text = formatRangeInsight({ estimatedRangeKm: 100, contributors: [], topRecommendation: null });
    expect(text).toContain("No recommendation available");
  });
});

describe("formatWhatIfInsight", () => {
  it("includes base, counterfactual, and the deterministic-simulation disclosure", () => {
    const text = formatWhatIfInsight(whatIfFixture());
    expect(text).toContain("VehicleGPT — Simulation Result");
    expect(text).toContain("Base:");
    expect(text).toContain("AGGRESSIVE_DRIVING");
    expect(text).toContain("Counterfactual:");
    expect(text).toContain("NORMAL_DRIVING");
    expect(text).toContain("not a prediction");
  });

  it("formats a positive range change with an explicit sign", () => {
    const text = formatWhatIfInsight(whatIfFixture({ estimated_range_change_km: 209.62 }));
    expect(text).toContain("+210 km");
  });

  it("reports charging scenarios as not applicable instead of a number", () => {
    const text = formatWhatIfInsight(whatIfFixture({ estimated_range_change_km: null }));
    expect(text).toContain("Not applicable");
  });

  it("never emits raw JSON", () => {
    const text = formatWhatIfInsight(whatIfFixture());
    expect(text).not.toMatch(/[{}]/);
  });
});
