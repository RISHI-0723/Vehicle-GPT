import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Drive, orderRecent } from "./Drive";
import { createFakeWorld } from "../test/fakeBackend";
import { driveRecordFixture, heroFixture } from "../test/fixtures";

describe("orderRecent", () => {
  it("always places the hero drive first", () => {
    const hero = driveRecordFixture({ simulationId: "hero", startTime: "2026-01-01T00:00:00Z" });
    const newer = driveRecordFixture({ simulationId: "newer", startTime: "2026-02-01T00:00:00Z" });
    const ordered = orderRecent([newer, hero], "hero");
    expect(ordered.map((d) => d.simulationId)).toEqual(["hero", "newer"]);
  });

  it("orders the remaining drives newest persisted first", () => {
    const older = driveRecordFixture({ simulationId: "older", startTime: "2026-01-01T00:00:00Z" });
    const newest = driveRecordFixture({ simulationId: "newest", startTime: "2026-03-01T00:00:00Z" });
    const mid = driveRecordFixture({ simulationId: "mid", startTime: "2026-02-01T00:00:00Z" });
    const ordered = orderRecent([older, newest, mid], "hero");
    expect(ordered.map((d) => d.simulationId)).toEqual(["newest", "mid", "older"]);
  });

  it("does not mutate the input array", () => {
    const drives = [driveRecordFixture({ simulationId: "a" }), driveRecordFixture({ simulationId: "b" })];
    const copy = [...drives];
    orderRecent(drives, "b");
    expect(drives).toEqual(copy);
  });
});

describe("Drive page AI actions", () => {
  it("links each AI action to the Ask screen with the question prefilled", () => {
    createFakeWorld([{ scenario: "NORMAL_DRIVING" }, { scenario: "AGGRESSIVE_DRIVING" }]);
    const hero = heroFixture();
    render(
      <MemoryRouter>
        <Drive hero={hero} drives={[hero.normal, hero.aggressive]} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /explain this drive/i })).toHaveAttribute(
      "href",
      `/ask?q=${encodeURIComponent("Why did my range drop?")}`,
    );
    expect(screen.getByRole("link", { name: /compare with normal/i })).toHaveAttribute(
      "href",
      `/ask?q=${encodeURIComponent("Was this worse than normal?")}`,
    );
    expect(screen.getByRole("link", { name: /what would improve this/i })).toHaveAttribute(
      "href",
      `/ask?q=${encodeURIComponent("What should I change?")}`,
    );
  });
});
