import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DemoProvider, useDemo } from "./DemoContext";
import { createFakeWorld } from "../test/fakeBackend";

function renderDemo() {
  return renderHook(() => useDemo(), { wrapper: DemoProvider });
}

describe("DemoProvider", () => {
  it("shows setup when no canonical demo data is persisted yet", async () => {
    createFakeWorld([]);
    const { result } = renderDemo();
    expect(result.current.status).toBe("checking");
    await waitFor(() => expect(result.current.status).toBe("setup"));
    expect(result.current.hero).toBeNull();
  });

  it("goes straight to ready when both canonical drives already exist", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const { result } = renderDemo();
    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(result.current.hero?.normal.scenario).toBe("NORMAL_DRIVING");
    expect(result.current.hero?.aggressive.scenario).toBe("AGGRESSIVE_DRIVING");
  });

  it("surfaces a safe error message when the readiness check fails", async () => {
    const world = createFakeWorld([]);
    world.offline = true;
    const { result } = renderDemo();
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.message).toBe("Vehicle intelligence is temporarily unavailable.");
  });

  it("prepare() creates both canonical drives in order and becomes ready", async () => {
    const world = createFakeWorld([]);
    const { result } = renderDemo();
    await waitFor(() => expect(result.current.status).toBe("setup"));

    act(() => result.current.prepare());
    expect(result.current.status).toBe("preparing");

    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(result.current.hero?.normal).not.toBeNull();
    expect(result.current.hero?.aggressive).not.toBeNull();

    const runCalls = world.calls.filter((c) => c.url.pathname === "/api/v1/simulation/run");
    expect(runCalls.map((c) => (c.body as { scenario: string }).scenario)).toEqual([
      "NORMAL_DRIVING",
      "AGGRESSIVE_DRIVING",
    ]);
  });

  it("resetDemo() clears the hero and returns to setup", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const { result } = renderDemo();
    await waitFor(() => expect(result.current.status).toBe("ready"));

    await act(async () => {
      await result.current.resetDemo();
    });

    expect(result.current.status).toBe("setup");
    expect(result.current.hero).toBeNull();
    expect(result.current.drives).toEqual([]);
  });

  it("recheck() re-runs the readiness check", async () => {
    createFakeWorld([]);
    const { result } = renderDemo();
    await waitFor(() => expect(result.current.status).toBe("setup"));

    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);

    act(() => result.current.recheck());
    await waitFor(() => expect(result.current.status).toBe("ready"));
  });
});
