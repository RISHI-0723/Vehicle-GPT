import { describe, expect, it } from "vitest";
import { routeAsk, SUGGESTED_PROMPTS, UNKNOWN_INTENT_COPY } from "./intents";

describe("routeAsk", () => {
  it("returns null for empty or whitespace-only input", () => {
    expect(routeAsk("")).toBeNull();
    expect(routeAsk("   ")).toBeNull();
  });

  it("returns null for input matching no rule", () => {
    expect(routeAsk("hello there")).toBeNull();
  });

  it("routes a range question to why-range", () => {
    expect(routeAsk("Why did my range drop?")?.intent).toBe("why-range");
    expect(routeAsk("my range dropped today")?.intent).toBe("why-range");
  });

  it("routes a what-if question to what-if, even when it also mentions range", () => {
    expect(routeAsk("What if I drove normally instead?")?.intent).toBe("what-if");
    expect(routeAsk("what if my range had been different")?.intent).toBe("what-if");
  });

  it("routes a cost question to cost", () => {
    expect(routeAsk("how much did this trip cost")?.intent).toBe("cost");
    expect(routeAsk("what did I spend on this drive")?.intent).toBe("cost");
    expect(routeAsk("₹ price please")?.intent).toBe("cost");
  });

  it("routes a stress question to battery-stress", () => {
    expect(routeAsk("Check battery stress")?.intent).toBe("battery-stress");
  });

  it("routes an anomaly question to anomaly", () => {
    expect(routeAsk("was my last drive unusual")?.intent).toBe("anomaly");
    expect(routeAsk("anything abnormal about my driving")?.intent).toBe("anomaly");
  });

  it("routes an energy question to energy", () => {
    expect(routeAsk("how much energy did I use")?.intent).toBe("energy");
    expect(routeAsk("kwh consumed")?.intent).toBe("energy");
  });

  it("is case-insensitive and trims whitespace", () => {
    expect(routeAsk("  WHY DID MY RANGE DROP  ")?.intent).toBe("why-range");
  });

  it("checks rules in priority order: what-if before why-range", () => {
    // Contains both "what if" and "why" wording; what-if must win per RULES ordering.
    expect(routeAsk("what if I understood why this happened")?.intent).toBe("what-if");
  });
});

describe("SUGGESTED_PROMPTS", () => {
  it("has a unique path for every suggested prompt", () => {
    const paths = SUGGESTED_PROMPTS.map((p) => p.path);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it("includes one prompt per supported intent", () => {
    const intents = SUGGESTED_PROMPTS.map((p) => p.intent).sort();
    expect(intents).toEqual(
      ["anomaly", "battery-stress", "cost", "energy", "what-if", "why-range"].sort(),
    );
  });
});

describe("UNKNOWN_INTENT_COPY", () => {
  it("is non-empty guidance copy", () => {
    expect(UNKNOWN_INTENT_COPY.length).toBeGreaterThan(0);
  });
});
