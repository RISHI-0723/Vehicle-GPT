import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { clearResourceCache } from "../lib/useResource";

afterEach(() => {
  cleanup();
  clearResourceCache();
  vi.unstubAllGlobals();
});
