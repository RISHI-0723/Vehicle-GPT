import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WhyRange } from "./WhyRange";
import { createFakeWorld } from "../test/fakeBackend";
import { heroFixture } from "../test/fixtures";

afterEach(() => {
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
});

describe("WhyRange page", () => {
  it("renders the explanation, baseline note and contributors once loaded", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const hero = heroFixture();
    render(
      <MemoryRouter>
        <WhyRange hero={hero} />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Significant efficiency drop/)).toBeInTheDocument();
    expect(screen.getAllByText("Compared with a matching normal drive.").length).toBeGreaterThan(0);
    expect(await screen.findByText("Aggressive driving")).toBeInTheDocument();
    expect(screen.getByText("CRITICAL IMPACT")).toBeInTheDocument();
  });

  it("lists key factors from the explanation", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    render(
      <MemoryRouter>
        <WhyRange hero={heroFixture()} />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/Aggressive driving score was 47.9/)).toBeInTheDocument();
  });

  it("copies a human-readable range insight to the clipboard, never raw JSON", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const user = userEvent.setup();
    // userEvent.setup() installs its own clipboard stub, so ours must be
    // defined after it to actually be the one the component sees.
    const writeText = vi.fn<(text: string) => Promise<void>>(async () => undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(
      <MemoryRouter>
        <WhyRange hero={heroFixture()} />
      </MemoryRouter>,
    );

    const button = await screen.findByRole("button", { name: /copy insight/i });
    await user.click(button);

    expect(await screen.findByText("Copied")).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledTimes(1);
    const copiedText = writeText.mock.calls[0][0] as string;
    expect(copiedText).toContain("VehicleGPT — Range Analysis");
    expect(copiedText).not.toMatch(/[{}]/);
  });
});
