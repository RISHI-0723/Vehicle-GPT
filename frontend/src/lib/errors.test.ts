import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { describeApiError } from "./errors";

function httpError(status: number): ApiError {
  return new ApiError("http", status, `HTTP ${status}`);
}

describe("describeApiError", () => {
  it("never shows the raw server detail for network failures", () => {
    const message = describeApiError(new ApiError("network", 0, "Network request failed"));
    expect(message).toBe("Vehicle intelligence is temporarily unavailable.");
  });

  it("gives the same safe copy for timeouts", () => {
    const message = describeApiError(new ApiError("timeout", 0, "Request timed out"));
    expect(message).toBe("Vehicle intelligence is temporarily unavailable.");
  });

  it.each([
    [400, "That request could not be processed. Check the values and try again."],
    [404, "No matching drive data is available yet."],
    [409, "A simulation is already running. Try again in a moment."],
    [422, "Some values are invalid. Check the inputs and try again."],
  ])("maps HTTP %i to a specific user-facing message", (status, expected) => {
    expect(describeApiError(httpError(status))).toBe(expected);
  });

  it("falls back to the generic message for unmapped HTTP statuses", () => {
    expect(describeApiError(httpError(500))).toBe("Vehicle intelligence is temporarily unavailable.");
    expect(describeApiError(httpError(503))).toBe("Vehicle intelligence is temporarily unavailable.");
  });
});
