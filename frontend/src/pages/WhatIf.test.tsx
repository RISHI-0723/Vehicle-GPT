import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WhatIf } from "./WhatIf";
import { createFakeWorld } from "../test/fakeBackend";
import { heroFixture } from "../test/fixtures";

afterEach(() => {
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
});

function renderWhatIf() {
  const hero = heroFixture();
  createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
  render(
    <MemoryRouter>
      <WhatIf hero={hero} />
    </MemoryRouter>,
  );
  return hero;
}

describe("WhatIf page", () => {
  it("runs the default normal-driving comparison and shows the range difference", async () => {
    const user = userEvent.setup();
    renderWhatIf();

    await user.click(screen.getByRole("button", { name: /what if i drove normally/i }));

    expect(await screen.findByText("+210 km")).toBeInTheDocument();
    expect(screen.getByText(/Potential difference/)).toBeInTheDocument();
  });

  it("shows charging metrics instead of a range comparison for the fast-charging scenario", async () => {
    const user = userEvent.setup();
    renderWhatIf();

    await user.click(screen.getByLabelText(/simulated fast charging/i));
    await user.click(screen.getByRole("button", { name: /what if i charged instead/i }));

    expect(await screen.findByText(/Range comparison is not applicable for charging sessions/)).toBeInTheDocument();
  });

  it("shows an error message when the comparison request fails", async () => {
    const hero = heroFixture();
    // No simulations registered at all: the hero ID the page requests does not exist server-side.
    createFakeWorld([]);
    render(
      <MemoryRouter>
        <WhatIf hero={hero} />
      </MemoryRouter>,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /what if i drove normally/i }));

    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThan(0);
    expect(alerts[0]).toHaveTextContent("No matching drive data is available yet.");
  });

  it("copies a human-readable simulation result to the clipboard", async () => {
    const user = userEvent.setup();
    // userEvent.setup() installs its own clipboard stub, so ours must be
    // defined after it to actually be the one the component sees.
    const writeText = vi.fn<(text: string) => Promise<void>>(async () => undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderWhatIf();

    await user.click(screen.getByRole("button", { name: /what if i drove normally/i }));
    await screen.findByText("+210 km");
    await user.click(screen.getByRole("button", { name: /copy simulation result/i }));

    expect(await screen.findByText("Copied")).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledTimes(1);
    const copiedText = writeText.mock.calls[0][0] as string;
    expect(copiedText).toContain("VehicleGPT — Simulation Result");
    expect(copiedText).toContain("not a prediction");
  });
});
