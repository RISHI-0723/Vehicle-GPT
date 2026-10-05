import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { Resource } from "../lib/useResource";
import { Async } from "./Async";

function resource<T>(overrides: Partial<Resource<T>>): Resource<T> {
  return { data: null, error: null, loading: false, stale: false, retry: vi.fn(), ...overrides };
}

describe("Async", () => {
  it("shows a loading skeleton while loading with no data yet", () => {
    render(<Async resource={resource({ loading: true })}>{() => <p>content</p>}</Async>);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("shows an error state with retry when loading fails with no data", () => {
    const retry = vi.fn();
    render(
      <Async resource={resource({ error: new ApiError("http", 404, "HTTP 404"), retry })}>
        {() => <p>content</p>}
      </Async>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("No matching drive data is available yet.");
    screen.getByRole("button", { name: /retry/i }).click();
    expect(retry).toHaveBeenCalled();
  });

  it("renders the content once data is present", () => {
    render(<Async resource={resource({ data: { v: 1 } })}>{(d) => <p>value {d.v}</p>}</Async>);
    expect(screen.getByText("value 1")).toBeInTheDocument();
  });

  it("shows a stale banner above the content when data is present but stale", () => {
    render(
      <Async resource={resource({ data: { v: 1 }, stale: true })}>{(d) => <p>value {d.v}</p>}</Async>,
    );
    expect(screen.getByText(/Showing last available data/)).toBeInTheDocument();
    expect(screen.getByText("value 1")).toBeInTheDocument();
  });

  it("shows the stale banner when data is present alongside an error, never the raw error", () => {
    render(
      <Async resource={resource({ data: { v: 1 }, error: new ApiError("network", 0, "x") })}>
        {(d) => <p>value {d.v}</p>}
      </Async>,
    );
    expect(screen.getByText(/Showing last available data/)).toBeInTheDocument();
  });

  it("renders nothing for the idle state (no key yet)", () => {
    const { container } = render(<Async resource={resource({})}>{() => <p>content</p>}</Async>);
    expect(container).toBeEmptyDOMElement();
  });
});
