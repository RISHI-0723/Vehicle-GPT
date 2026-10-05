import { describe, expect, it } from "vitest";
import { buildDriveReportMarkdown, driveReportFilename } from "./exportReport";
import { driveRecordFixture, vehicleFixture, whyFixture } from "../test/fixtures";

function build() {
  return buildDriveReportMarkdown({
    vehicle: vehicleFixture(),
    drive: driveRecordFixture(),
    summary: whyFixture(),
  });
}

describe("buildDriveReportMarkdown", () => {
  it("starts with the required top-level heading", () => {
    expect(build().startsWith("# VehicleGPT Drive Report")).toBe(true);
  });

  it("includes every required section", () => {
    const text = build();
    for (const section of [
      "## Vehicle",
      "## Simulation",
      "## Energy",
      "## Range",
      "## Intelligence",
      "## Contributors",
      "## Recommendations",
      "## Disclosure",
    ]) {
      expect(text).toContain(section);
    }
  });

  it("includes the simulation-vs-live-data disclaimer", () => {
    const text = build();
    expect(text).toContain("Synthetic simulated telemetry");
    expect(text).toContain("not live vehicle data");
    expect(text).toContain("Counterfactual results are simulations, not predictions");
  });

  it("includes real vehicle and simulation identifiers, not placeholders", () => {
    const vehicle = vehicleFixture();
    const drive = driveRecordFixture();
    const text = build();
    expect(text).toContain(vehicle.vehicle_id);
    expect(text).toContain(drive.simulationId);
  });

  it("never includes a secret, token, or API key", () => {
    const text = build();
    expect(text.toLowerCase()).not.toMatch(/api[_-]?key|secret|token|password/);
  });

  it("lists up to five recommendations, most relevant first", () => {
    const text = build();
    const summary = whyFixture();
    expect(summary.recommendations.recommendations.length).toBeGreaterThan(0);
    expect(text).toContain(summary.recommendations.recommendations[0].title);
  });
});

describe("driveReportFilename", () => {
  it("is a markdown file named after the simulation", () => {
    const filename = driveReportFilename(driveRecordFixture());
    expect(filename.endsWith(".md")).toBe(true);
    expect(filename).toContain(driveRecordFixture().simulationId);
  });
});
