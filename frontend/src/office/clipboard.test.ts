import { afterEach, describe, expect, it, vi } from "vitest";
import { writeToClipboard } from "./clipboard";

function stubClipboard(writeText: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText },
    configurable: true,
  });
}

afterEach(() => {
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
});

describe("writeToClipboard", () => {
  it("returns true and writes the exact text when the Clipboard API succeeds", async () => {
    const writeText = vi.fn(async () => undefined);
    stubClipboard(writeText);

    const ok = await writeToClipboard("hello world");

    expect(ok).toBe(true);
    expect(writeText).toHaveBeenCalledWith("hello world");
  });

  it("returns false when the Clipboard API is unavailable", async () => {
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    expect(await writeToClipboard("x")).toBe(false);
  });

  it("returns false when the Clipboard API rejects (e.g. permission denied)", async () => {
    stubClipboard(async () => {
      throw new Error("denied");
    });
    expect(await writeToClipboard("x")).toBe(false);
  });
});
