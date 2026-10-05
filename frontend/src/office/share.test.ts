import { afterEach, describe, expect, it, vi } from "vitest";
import { shareText } from "./share";

afterEach(() => {
  Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
});

describe("shareText", () => {
  it("uses the Web Share API when available", async () => {
    const share = vi.fn(async () => undefined);
    Object.defineProperty(navigator, "share", { value: share, configurable: true });

    const outcome = await shareText("Title", "Body text");

    expect(outcome).toBe("shared");
    expect(share).toHaveBeenCalledWith({ title: "Title", text: "Body text" });
  });

  it("reports cancelled when the user dismisses the native share sheet", async () => {
    Object.defineProperty(navigator, "share", {
      value: vi.fn(async () => {
        throw new DOMException("cancelled", "AbortError");
      }),
      configurable: true,
    });

    expect(await shareText("Title", "Body")).toBe("cancelled");
  });

  it("falls back to the clipboard when the Web Share API is unavailable", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn(async () => undefined) },
      configurable: true,
    });

    expect(await shareText("Title", "Body")).toBe("copied");
  });

  it("reports unavailable when neither share nor clipboard work", async () => {
    expect(await shareText("Title", "Body")).toBe("unavailable");
  });
});
