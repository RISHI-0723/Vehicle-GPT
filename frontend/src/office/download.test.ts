import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { downloadTextFile } from "./download";

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:mock-url");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("downloadTextFile", () => {
  it("creates and clicks a temporary anchor pointing at the generated blob URL", () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    downloadTextFile("report.md", "# Hello");

    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");

    clickSpy.mockRestore();
  });

  it("does not leave the temporary anchor attached to the document", () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const before = document.querySelectorAll("a").length;

    downloadTextFile("report.md", "content");

    expect(document.querySelectorAll("a").length).toBe(before);
    vi.restoreAllMocks();
  });
});
