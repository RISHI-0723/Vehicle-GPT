import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { useResource } from "./useResource";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (err: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useResource", () => {
  it("starts in a loading state and resolves with the loaded data", async () => {
    const { promise, resolve } = deferred<{ v: number }>();
    const { result } = renderHook(() => useResource("k1", () => promise));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    await act(async () => {
      resolve({ v: 1 });
      await promise;
    });

    await waitFor(() => expect(result.current.data).toEqual({ v: 1 }));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("does not load when the key is null", () => {
    const load = vi.fn(async () => ({ v: 1 }));
    const { result } = renderHook(() => useResource(null, load));
    expect(load).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it("surfaces an error with no stale data when nothing was cached yet", async () => {
    const error = new ApiError("http", 404, "HTTP 404");
    const { result } = renderHook(() => useResource("k2", () => Promise.reject(error)));

    await waitFor(() => expect(result.current.error).toBe(error));
    expect(result.current.data).toBeNull();
    expect(result.current.stale).toBe(false);
  });

  it("marks data stale on a network failure after a prior success, keeping the last-good data", async () => {
    let call = 0;
    const load = () => {
      call += 1;
      if (call === 1) return Promise.resolve({ v: "first" });
      return Promise.reject(new ApiError("network", 0, "Network request failed"));
    };
    const { result, rerender } = renderHook(({ key }: { key: string }) => useResource(key, load), {
      initialProps: { key: "k3" },
    });

    await waitFor(() => expect(result.current.data).toEqual({ v: "first" }));

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.data).toEqual({ v: "first" });
    expect(result.current.stale).toBe(true);
    rerender({ key: "k3" });
  });

  it("does not mark data stale when the retry fails with an HTTP error", async () => {
    let call = 0;
    const load = () => {
      call += 1;
      if (call === 1) return Promise.resolve({ v: "first" });
      return Promise.reject(new ApiError("http", 500, "HTTP 500"));
    };
    const { result } = renderHook(() => useResource("k4", load));

    await waitFor(() => expect(result.current.data).toEqual({ v: "first" }));

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.data).toEqual({ v: "first" });
    expect(result.current.stale).toBe(false);
  });

  it("reloads when the key changes", async () => {
    const load = vi.fn(async (key: string) => ({ key }));
    const { result, rerender } = renderHook(({ key }: { key: string }) => useResource(key, () => load(key)), {
      initialProps: { key: "a" },
    });

    await waitFor(() => expect(result.current.data).toEqual({ key: "a" }));

    rerender({ key: "b" });
    await waitFor(() => expect(result.current.data).toEqual({ key: "b" }));
    expect(load).toHaveBeenCalledTimes(2);
  });
});
