import { describe, expect, it, vi } from "vitest";
import { ApiError, requestJson, toApiError, withQuery } from "./client";

describe("withQuery", () => {
  it("appends no query string when there are no defined params", () => {
    expect(withQuery("/path", {})).toBe("/path");
    expect(withQuery("/path", { a: undefined })).toBe("/path");
  });

  it("builds a query string from defined params only", () => {
    expect(withQuery("/path", { a: 1, b: "x", c: undefined })).toBe("/path?a=1&b=x");
  });
});

describe("toApiError", () => {
  it("passes an existing ApiError through unchanged", () => {
    const original = new ApiError("http", 404, "HTTP 404");
    expect(toApiError(original)).toBe(original);
  });

  it("wraps any other error as a generic network failure", () => {
    const wrapped = toApiError(new Error("boom"));
    expect(wrapped.kind).toBe("network");
    expect(wrapped.status).toBe(0);
  });
});

describe("requestJson", () => {
  it("resolves with the parsed JSON body on a 2xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
    );
    await expect(requestJson<{ ok: boolean }>("/x")).resolves.toEqual({ ok: true });
  });

  it("throws an http ApiError carrying the response status, never the raw body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "internal secret" }), { status: 404 })),
    );
    try {
      await requestJson("/x");
      throw new Error("expected requestJson to throw");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiError = err as ApiError;
      expect(apiError.kind).toBe("http");
      expect(apiError.status).toBe(404);
      expect(apiError.message).not.toContain("internal secret");
    }
  });

  it("classifies a thrown network failure as kind 'network'", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    try {
      await requestJson("/x");
      throw new Error("expected requestJson to throw");
    } catch (err) {
      expect((err as ApiError).kind).toBe("network");
      expect((err as ApiError).status).toBe(0);
    }
  });

  it("classifies an aborted request as kind 'timeout'", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new DOMException("The operation was aborted", "AbortError");
      }),
    );
    try {
      await requestJson("/x");
      throw new Error("expected requestJson to throw");
    } catch (err) {
      expect((err as ApiError).kind).toBe("timeout");
    }
  });

  it("sends a JSON content-type header only when a body is present", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await requestJson("/no-body");
    const [, getInit] = fetchMock.mock.calls[0];
    expect((getInit?.headers as Record<string, string>)["Content-Type"]).toBeUndefined();

    await requestJson("/with-body", { method: "POST", body: { a: 1 } });
    const [, postInit] = fetchMock.mock.calls[1];
    expect((postInit?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(postInit?.body).toBe(JSON.stringify({ a: 1 }));
  });
});
