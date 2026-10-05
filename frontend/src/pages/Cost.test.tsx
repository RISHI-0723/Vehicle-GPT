import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Cost, parseElectricityPrice } from "./Cost";
import { DEMO_VEHICLE_ID } from "../demo/config";
import { createFakeWorld } from "../test/fakeBackend";
import { heroFixture } from "../test/fixtures";

describe("parseElectricityPrice", () => {
  it("requires a non-empty value", () => {
    expect(parseElectricityPrice("")).toEqual({
      error: "Enter an electricity price in ₹ per kWh to calculate cost.",
    });
    expect(parseElectricityPrice("   ")).toEqual({
      error: "Enter an electricity price in ₹ per kWh to calculate cost.",
    });
  });

  it("rejects non-numeric input", () => {
    expect(parseElectricityPrice("abc")).toEqual({
      error: "Enter an electricity price in ₹ per kWh to calculate cost.",
    });
  });

  it("rejects zero and negative values", () => {
    expect(parseElectricityPrice("0")).toEqual({ error: "Electricity price must be greater than zero." });
    expect(parseElectricityPrice("-5")).toEqual({ error: "Electricity price must be greater than zero." });
  });

  it("accepts a valid positive price", () => {
    expect(parseElectricityPrice("8.5")).toEqual({ value: 8.5 });
  });
});

describe("Cost page", () => {
  it("shows a validation error and never calls the backend for an empty price", async () => {
    createFakeWorld([]);
    const user = userEvent.setup();
    render(<Cost hero={heroFixture()} />);

    await user.click(screen.getByRole("button", { name: /calculate trip cost/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Enter an electricity price in ₹ per kWh to calculate cost.",
    );
  });

  it("submits the price and renders the backend's cost result", async () => {
    const world = createFakeWorld([]);
    const user = userEvent.setup();
    const hero = heroFixture();
    render(<Cost hero={hero} />);

    await user.type(screen.getByLabelText(/electricity price/i), "8");
    await user.click(screen.getByRole("button", { name: /calculate trip cost/i }));

    expect(await screen.findByText(/Estimated operating cost/)).toBeInTheDocument();

    const costCall = world.calls.find((c) => c.url.pathname === "/api/v1/intelligence/cost");
    expect(costCall?.body).toEqual({
      vehicle_id: DEMO_VEHICLE_ID,
      simulation_id: hero.aggressive.simulationId,
      electricity_price_per_kwh: 8,
    });
  });

  it("maps a server validation rejection to the price-specific message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "rejected" }), { status: 422 })),
    );
    const user = userEvent.setup();
    render(<Cost hero={heroFixture()} />);

    await user.type(screen.getByLabelText(/electricity price/i), "5");
    await user.click(screen.getByRole("button", { name: /calculate trip cost/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Electricity price must be greater than zero.",
    );
  });
});
