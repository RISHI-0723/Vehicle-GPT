import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { DemoSetup } from "./DemoSetup";
import { DemoProvider } from "../demo/DemoContext";
import { createFakeWorld } from "../test/fakeBackend";

describe("DemoSetup page", () => {
  it("offers to prepare the demo when no canonical data exists, and never auto-runs it", async () => {
    const world = createFakeWorld([]);
    render(
      <DemoProvider>
        <DemoSetup />
      </DemoProvider>,
    );

    const button = await screen.findByRole("button", { name: /prepare demo/i });
    expect(world.calls.filter((c) => c.method === "POST")).toHaveLength(0);

    const user = userEvent.setup();
    await user.click(button);

    await waitFor(() => expect(world.calls.some((c) => c.method === "POST")).toBe(true));
  });

  it("shows a retry control when the readiness check fails", async () => {
    const world = createFakeWorld([]);
    world.offline = true;
    render(
      <DemoProvider>
        <DemoSetup />
      </DemoProvider>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Vehicle intelligence is temporarily unavailable.",
    );
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
