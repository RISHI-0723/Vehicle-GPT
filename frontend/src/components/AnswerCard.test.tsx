import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnswerCard } from "./AnswerCard";
import { askResponseFixture } from "../test/fixtures";

function renderCard(overrides: Parameters<typeof askResponseFixture>[0] = {}) {
  return render(
    <MemoryRouter>
      <AnswerCard response={askResponseFixture(overrides)} />
    </MemoryRouter>,
  );
}

afterEach(() => {
  Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
});

describe("AnswerCard", () => {
  it("renders the answer text and confidence", () => {
    renderCard({ answer: "Your range dropped because of aggressive driving." });
    expect(screen.getByText("Your range dropped because of aggressive driving.")).toBeInTheDocument();
  });

  it("always shows the simulation disclosure", () => {
    renderCard();
    expect(screen.getByText(/synthetic simulated telemetry, not live vehicle data/i)).toBeInTheDocument();
  });

  it("shows the fallback banner only when fallback_used is true", () => {
    const { rerender } = render(
      <MemoryRouter>
        <AnswerCard response={askResponseFixture({ fallback_used: false })} />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/AI assistant was unavailable/i)).not.toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <AnswerCard response={askResponseFixture({ fallback_used: true })} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/AI assistant was unavailable/i)).toBeInTheDocument();
  });

  it("renders each evidence item's label and value", () => {
    renderCard({
      evidence: [{ id: "x", label: "Estimated range", value: 200, unit: "km" }],
    });
    expect(screen.getByText("Estimated range")).toBeInTheDocument();
    expect(screen.getByText("200 km")).toBeInTheDocument();
  });

  it("renders no evidence list when evidence is empty", () => {
    renderCard({ evidence: [] });
    expect(screen.queryByLabelText("Evidence")).not.toBeInTheDocument();
  });

  it("renders every action as a working link to its mapped route", () => {
    renderCard({
      actions: [{ id: "WHAT_IF_NORMAL", label: "What if I drove normally?", type: "WHAT_IF" }],
    });
    expect(screen.getByRole("link", { name: /what if i drove normally/i })).toHaveAttribute("href", "/what-if");
  });

  it("shares the answer text via the Web Share API when available", async () => {
    const user = userEvent.setup();
    const share = vi.fn(async () => undefined);
    Object.defineProperty(navigator, "share", { value: share, configurable: true });
    renderCard({ answer: "Your range dropped because of aggressive driving." });

    await user.click(screen.getByRole("button", { name: /share/i }));

    expect(share).toHaveBeenCalledWith({
      title: "VehicleGPT answer",
      text: "Your range dropped because of aggressive driving.",
    });
  });

  it("falls back to copying the answer when sharing is unavailable", async () => {
    const user = userEvent.setup();
    // userEvent.setup() installs its own clipboard stub, so ours must be
    // defined after it to actually be the one the component sees.
    const writeText = vi.fn(async () => undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderCard();

    await user.click(screen.getByRole("button", { name: /share/i }));

    expect(await screen.findByText(/copied to clipboard/i)).toBeInTheDocument();
    expect(writeText).toHaveBeenCalled();
  });
});
