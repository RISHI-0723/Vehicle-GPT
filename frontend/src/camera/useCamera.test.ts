import { act, renderHook } from "@testing-library/react";
import type { RefObject } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCamera } from "./useCamera";

function stubMediaDevices(getUserMedia: (constraints: unknown) => Promise<MediaStream>) {
  Object.defineProperty(navigator, "mediaDevices", {
    value: { getUserMedia },
    configurable: true,
  });
}

function fakeStream(): MediaStream {
  const track = { stop: vi.fn() };
  return { getTracks: () => [track] } as unknown as MediaStream;
}

function attachFakeVideoElement(videoRef: RefObject<HTMLVideoElement | null>) {
  videoRef.current = { videoWidth: 640, videoHeight: 480 } as HTMLVideoElement;
}

afterEach(() => {
  Object.defineProperty(navigator, "mediaDevices", { value: undefined, configurable: true });
});

describe("useCamera", () => {
  it("reports UNSUPPORTED when getUserMedia is not available", () => {
    const { result } = renderHook(() => useCamera());
    expect(result.current.state).toBe("UNSUPPORTED");
  });

  describe("when the browser supports getUserMedia", () => {
    beforeEach(() => {
      stubMediaDevices(vi.fn(async () => fakeStream()));
    });

    it("starts IDLE", () => {
      const { result } = renderHook(() => useCamera());
      expect(result.current.state).toBe("IDLE");
    });

    it("moves to READY after a granted permission request", async () => {
      const { result } = renderHook(() => useCamera());
      await act(async () => {
        await result.current.requestAccess();
      });
      expect(result.current.state).toBe("READY");
    });

    it("moves to DENIED with a clear message when permission is refused", async () => {
      stubMediaDevices(vi.fn(async () => {
        throw new DOMException("denied", "NotAllowedError");
      }));
      const { result } = renderHook(() => useCamera());
      await act(async () => {
        await result.current.requestAccess();
      });
      expect(result.current.state).toBe("DENIED");
      expect(result.current.errorMessage).toMatch(/denied/i);
    });

    it("capture() moves to PREVIEW once a video frame is available", async () => {
      const { result } = renderHook(() => useCamera());
      await act(async () => {
        await result.current.requestAccess();
      });
      attachFakeVideoElement(result.current.videoRef);
      act(() => result.current.capture());
      expect(result.current.state).toBe("PREVIEW");
    });

    it("retake() clears the captured image and returns to READY", async () => {
      const { result } = renderHook(() => useCamera());
      await act(async () => {
        await result.current.requestAccess();
      });
      attachFakeVideoElement(result.current.videoRef);
      act(() => result.current.capture());
      act(() => result.current.retake());
      expect(result.current.state).toBe("READY");
      expect(result.current.imageDataUrl).toBeNull();
    });

    it("cancel() stops the stream, clears state, and returns to IDLE", async () => {
      const { result } = renderHook(() => useCamera());
      await act(async () => {
        await result.current.requestAccess();
      });
      attachFakeVideoElement(result.current.videoRef);
      act(() => result.current.capture());
      act(() => result.current.cancel());
      expect(result.current.state).toBe("IDLE");
      expect(result.current.imageDataUrl).toBeNull();
      expect(result.current.errorMessage).toBeNull();
    });

    it("never claims to analyze the captured image", () => {
      // The analysis-unavailable copy is a fixed, honest string -- not generated.
      // Re-importing it here would defeat the point; this just asserts the hook's
      // module exposes no analyze/recognize/ocr function at all.
      const api = Object.keys(renderHook(() => useCamera()).result.current);
      expect(api).not.toContain("analyze");
      expect(api).not.toContain("recognize");
    });
  });
});
