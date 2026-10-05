import { describe, expect, it } from "vitest";
import {
  anomalyCopy,
  baselineCopy,
  confidenceCopy,
  formatInr,
  formatKm,
  formatKwh,
  formatMinutes,
  formatPercent,
  formatSignedKm,
  impactCopy,
  scenarioLabel,
  stressCopy,
} from "./format";

describe("formatKm", () => {
  it("rounds to the nearest km and appends the unit", () => {
    expect(formatKm(226.73)).toBe("227 km");
    expect(formatKm(0)).toBe("0 km");
  });
});

describe("formatSignedKm", () => {
  it("prefixes a plus sign for positive values", () => {
    expect(formatSignedKm(209.62)).toBe("+210 km");
  });

  it("does not prefix a plus sign for negative or zero values", () => {
    expect(formatSignedKm(-12.4)).toBe("-12 km");
    expect(formatSignedKm(0)).toBe("0 km");
  });
});

describe("formatKwh", () => {
  it("formats with exactly two decimal places", () => {
    expect(formatKwh(11.4634)).toBe("11.46 kWh");
    expect(formatKwh(3)).toBe("3.00 kWh");
  });
});

describe("formatPercent", () => {
  it("formats with one decimal place", () => {
    expect(formatPercent(81.16)).toBe("81.2%");
  });
});

describe("formatInr", () => {
  it("formats using the Indian rupee currency format", () => {
    expect(formatInr(87.71)).toContain("87.71");
    expect(formatInr(87.71)).toContain("₹");
  });
});

describe("formatMinutes", () => {
  it("rounds minutes and appends the unit", () => {
    expect(formatMinutes(30.4)).toBe("30 min");
  });

  it("reports unavailable duration for null", () => {
    expect(formatMinutes(null)).toBe("Duration unavailable");
  });
});

describe("scenarioLabel", () => {
  it("maps every known scenario to its label", () => {
    expect(scenarioLabel("NORMAL_DRIVING")).toBe("Normal Drive");
    expect(scenarioLabel("AGGRESSIVE_DRIVING")).toBe("Aggressive Drive");
    expect(scenarioLabel("HOT_INDIAN_DAY")).toBe("Hot Day Drive");
    expect(scenarioLabel("ENERGY_ANOMALY")).toBe("Energy Anomaly Drive");
    expect(scenarioLabel("FAST_CHARGING")).toBe("Simulated Charging");
  });

  it("falls back for unknown or null scenarios", () => {
    expect(scenarioLabel("SOMETHING_ELSE")).toBe("Unidentified Drive");
    expect(scenarioLabel(null)).toBe("Unidentified Drive");
  });
});

describe("baselineCopy", () => {
  it("never presents an approximate match as exact", () => {
    expect(baselineCopy("EXACT")).toMatch(/matching normal drive/);
    expect(baselineCopy("APPROXIMATE")).toMatch(/closest recent/);
    expect(baselineCopy("APPROXIMATE")).not.toMatch(/matching normal drive/);
    expect(baselineCopy("UNAVAILABLE")).toMatch(/Not enough/);
  });
});

describe("confidenceCopy", () => {
  it("suppresses extra copy for HIGH confidence", () => {
    expect(confidenceCopy("HIGH")).toBeNull();
  });

  it("flags limited comparison data for lower confidence", () => {
    expect(confidenceCopy("MEDIUM")).toBe("Limited comparison data.");
    expect(confidenceCopy("LOW")).toBe("Limited comparison data.");
  });
});

describe("stressCopy", () => {
  it("maps every stress level to display text", () => {
    expect(stressCopy("LOW")).toBe("Low");
    expect(stressCopy("MODERATE")).toBe("Moderate");
    expect(stressCopy("ELEVATED")).toBe("Elevated");
    expect(stressCopy("HIGH")).toBe("High");
    expect(stressCopy("CRITICAL")).toBe("Critical");
  });
});

describe("impactCopy", () => {
  it("reports no baseline comparison when unavailable", () => {
    expect(impactCopy("UNAVAILABLE")).toBe("No baseline comparison");
  });

  it("appends IMPACT for every other level", () => {
    expect(impactCopy("CRITICAL")).toBe("CRITICAL IMPACT");
    expect(impactCopy("LOW")).toBe("LOW IMPACT");
  });
});

describe("anomalyCopy", () => {
  it("uses the backend flag, never an inferred diagnosis", () => {
    expect(anomalyCopy(true)).toBe("Your energy use is higher than expected.");
    expect(anomalyCopy(false)).toBe("Your recent drive looks normal.");
  });
});
