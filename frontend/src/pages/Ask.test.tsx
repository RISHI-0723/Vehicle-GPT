import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Ask } from "./Ask";
import { createFakeWorld } from "../test/fakeBackend";

class FakeSpeechRecognition {
  static instances: FakeSpeechRecognition[] = [];
  lang = "";
  interimResults = false;
  continuous = false;
  onresult: ((event: unknown) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn(() => {
    this.onend?.();
  });

  constructor() {
    FakeSpeechRecognition.instances.push(this);
  }
}

function renderAsk() {
  return render(
    <MemoryRouter initialEntries={["/ask"]}>
      <Routes>
        <Route path="/ask" element={<Ask />} />
        <Route path="/why-range" element={<div>Why-range screen</div>} />
        <Route path="/what-if" element={<div>What-if screen</div>} />
        <Route path="/cost" element={<div>Cost screen</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Ask page", () => {
  it("shows an answer card with evidence, confidence and actions for a recognized question", async () => {
    createFakeWorld([]);
    const user = userEvent.setup();
    renderAsk();

    await user.type(screen.getByLabelText(/ask about your vehicle/i), "Why did my range drop?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    const heading = await screen.findByRole("heading", { name: "Answer" });
    const answerCard = heading.closest("section") as HTMLElement;
    expect(within(answerCard).getByText(/aggressive driving/i)).toBeInTheDocument();
    expect(within(answerCard).getByText("Energy consumption")).toBeInTheDocument();
    expect(within(answerCard).getByRole("link", { name: /what if i drove normally/i })).toHaveAttribute(
      "href",
      "/what-if",
    );
    expect(within(answerCard).getByRole("link", { name: /see main contributors/i })).toHaveAttribute(
      "href",
      "/why-range",
    );
    expect(within(answerCard).getByText(/synthetic simulated telemetry, not live vehicle data/i)).toBeInTheDocument();
  });

  it("shows the deterministic fallback banner and capability copy for an unrecognized question", async () => {
    createFakeWorld([]);
    const user = userEvent.setup();
    renderAsk();

    await user.type(screen.getByLabelText(/ask about your vehicle/i), "tell me a joke");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    const heading = await screen.findByRole("heading", { name: "Answer" });
    const answerCard = heading.closest("section") as HTMLElement;
    expect(within(answerCard).getByText(/I can help with range, efficiency/i)).toBeInTheDocument();
    expect(within(answerCard).getByText(/AI assistant was unavailable/i)).toBeInTheDocument();
  });

  it("offers the Cost screen instead of calculating when no price is in context", async () => {
    createFakeWorld([]);
    const user = userEvent.setup();
    renderAsk();

    await user.type(screen.getByLabelText(/ask about your vehicle/i), "How much did that drive cost?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    const heading = await screen.findByRole("heading", { name: "Answer" });
    const answerCard = heading.closest("section") as HTMLElement;
    expect(within(answerCard).getByText(/enter your electricity price/i)).toBeInTheDocument();
    expect(within(answerCard).getByRole("link", { name: /calculate drive cost/i })).toHaveAttribute("href", "/cost");
  });

  it("shows the what-if range comparison for a what-if question", async () => {
    createFakeWorld([]);
    const user = userEvent.setup();
    renderAsk();

    await user.type(screen.getByLabelText(/ask about your vehicle/i), "What if I drove normally?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Estimated range difference")).toBeInTheDocument();
  });

  it("records the exchange in recent conversation after answering", async () => {
    createFakeWorld([]);
    const user = userEvent.setup();
    renderAsk();

    await user.type(screen.getByLabelText(/ask about your vehicle/i), "Why did my range drop?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await screen.findByRole("heading", { name: "Answer" });

    const conversationHeading = screen.getByRole("heading", { name: "Recent conversation" });
    expect(conversationHeading).toBeInTheDocument();
    const conversationSection = conversationHeading.closest("section") as HTMLElement;
    expect(within(conversationSection).getByText("Why did my range drop?")).toBeInTheDocument();
  });

  it("shows an error state when the ask request fails", async () => {
    const world = createFakeWorld([]);
    world.offline = true;
    const user = userEvent.setup();
    renderAsk();

    await user.type(screen.getByLabelText(/ask about your vehicle/i), "Why did my range drop?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("lists suggested prompts as working links", () => {
    createFakeWorld([]);
    renderAsk();
    expect(screen.getByRole("link", { name: /what if i drove normally/i })).toHaveAttribute("href", "/what-if");
    expect(screen.getByRole("link", { name: /why did my range drop/i })).toHaveAttribute("href", "/why-range");
  });

  it("disables the microphone and explains when voice input is unavailable", () => {
    createFakeWorld([]);
    renderAsk();
    expect(screen.getByRole("button", { name: /ask by voice/i })).toBeDisabled();
    expect(screen.getByText(/voice input isn't available here/i)).toBeInTheDocument();
  });

  it("fills the input from a voice transcript once recognition finishes", async () => {
    FakeSpeechRecognition.instances = [];
    vi.stubGlobal("SpeechRecognition", FakeSpeechRecognition);
    createFakeWorld([]);
    const user = userEvent.setup();
    renderAsk();

    await user.click(screen.getByRole("button", { name: /ask by voice/i }));
    expect(screen.getByText(/listening/i)).toBeInTheDocument();

    const recognition = FakeSpeechRecognition.instances[0];
    recognition.onresult?.({ results: [[{ transcript: "Why did my range drop?" }]] });

    expect(await screen.findByDisplayValue("Why did my range drop?")).toBeInTheDocument();
  });
});
