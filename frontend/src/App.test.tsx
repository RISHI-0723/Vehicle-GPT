import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "./App";
import { createFakeWorld } from "./test/fakeBackend";

beforeEach(() => {
  window.history.pushState({}, "", "/");
});

describe("App", () => {
  it("shows the demo setup screen until canonical demo data is ready", async () => {
    createFakeWorld([]);
    render(<App />);
    expect(await screen.findByRole("button", { name: /prepare demo/i })).toBeInTheDocument();
  });

  it("prepares the demo and reaches the Home screen", async () => {
    createFakeWorld([]);
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: /prepare demo/i }));

    expect(await screen.findByText(/persisted simulated drives?/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /what happened/i })).toBeInTheDocument();
  });

  it("goes straight to the Home screen when canonical demo data already exists", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    render(<App />);
    expect(await screen.findByText(/persisted simulated drives?/)).toBeInTheDocument();
  });

  it("shows a not-found screen with a way back home for an unknown route", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    window.history.pushState({}, "", "/does-not-exist");
    render(<App />);

    expect(await screen.findByText("Page not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go to home/i })).toHaveAttribute("href", "/");
  });

  it("renders the Ask screen at /ask once the demo is ready", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    window.history.pushState({}, "", "/ask");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Ask VehicleGPT" })).toBeInTheDocument();
  });
});
