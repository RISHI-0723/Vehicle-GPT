import type { ApiError } from "../api/client";

/** User-facing copy for every failure class. Raw bodies and stack traces are never shown. */
export function describeApiError(error: ApiError): string {
  if (error.kind === "network" || error.kind === "timeout") {
    return "Vehicle intelligence is temporarily unavailable.";
  }
  switch (error.status) {
    case 400:
      return "That request could not be processed. Check the values and try again.";
    case 404:
      return "No matching drive data is available yet.";
    case 409:
      return "A simulation is already running. Try again in a moment.";
    case 422:
      return "Some values are invalid. Check the inputs and try again.";
    default:
      return "Vehicle intelligence is temporarily unavailable.";
  }
}
