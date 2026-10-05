import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Home } from "./Home";
import { createFakeWorld } from "../test/fakeBackend";
import { heroFixture } from "../test/fixtures";

describe("Home page", () => {
  it("shows the hero range, explanation and a top recommendation once loaded", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const hero = heroFixture();
    render(
      <MemoryRouter>
        <Home hero={hero} drives={[hero.normal, hero.aggressive]} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/2 persisted simulated drives/)).toBeInTheDocument();
    expect(await screen.findByLabelText("Estimated range 227 km")).toBeInTheDocument();
    expect(await screen.findByText(/Significant efficiency drop/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /what if i drove normally/i })).toHaveAttribute(
      "href",
      "/what-if",
    );
  });

  it("links the hero range card to the why-range screen", async () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const hero = heroFixture();
    render(
      <MemoryRouter>
        <Home hero={hero} drives={[hero.normal, hero.aggressive]} />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("link", { name: /why did my range change/i })).toHaveAttribute(
      "href",
      "/why-range",
    );
  });

  it("offers an Ask your vehicle entry point with the question prefilled", () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const hero = heroFixture();
    render(
      <MemoryRouter>
        <Home hero={hero} drives={[hero.normal, hero.aggressive]} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /ask your vehicle/i })).toHaveAttribute(
      "href",
      `/ask?q=${encodeURIComponent("Why did my range drop?")}`,
    );
  });
});
