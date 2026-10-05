import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Vehicle } from "./Vehicle";
import { DemoProvider } from "../demo/DemoContext";
import { createFakeWorld } from "../test/fakeBackend";
import { heroFixture } from "../test/fixtures";

function renderVehicle() {
  const hero = heroFixture();
  render(
    <MemoryRouter>
      <DemoProvider>
        <Vehicle hero={hero} />
      </DemoProvider>
    </MemoryRouter>,
  );
  return hero;
}

describe("Vehicle page", () => {
  it("shows vehicle details and operating stress once loaded", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    renderVehicle();

    expect(await screen.findByRole("heading", { name: "VehicleGPT EV Demo" })).toBeInTheDocument();
    expect(await screen.findByText("Elevated")).toBeInTheDocument();
    expect(screen.getByText(/This is not battery health, degradation, or remaining life/)).toBeInTheDocument();
  });

  it("requires a confirmation step before resetting the demo", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const user = userEvent.setup();
    renderVehicle();

    await user.click(screen.getByRole("button", { name: "Reset Demo" }));
    expect(screen.getByRole("button", { name: "Confirm reset" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("button", { name: "Confirm reset" })).not.toBeInTheDocument();
  });

  it("distinguishes known, simulated, and unavailable data", () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    renderVehicle();

    expect(screen.getByText(/KNOWN — fixed demo configuration/)).toBeInTheDocument();
    expect(screen.getByText(/SIMULATED — synthetic telemetry/)).toBeInTheDocument();
    expect(screen.getByText(/UNAVAILABLE — not connected/)).toBeInTheDocument();
  });

  it("enables the export button only once vehicle and intelligence data are loaded, then downloads a report", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const user = userEvent.setup();
    renderVehicle();

    const exportButton = screen.getByRole("button", { name: /export drive report/i });
    expect(exportButton).toBeDisabled();

    await waitFor(() => expect(exportButton).toBeEnabled());
    await user.click(exportButton);

    expect(clickSpy).toHaveBeenCalledTimes(1);
    clickSpy.mockRestore();
  });
});
