import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSpeechRecognition } from "./useSpeechRecognition";

class FakeSpeechRecognition {
  static instances: FakeSpeechRecognition[] = [];
  lang = "";
  interimResults = false;
  continuous = false;
  onresult: ((event: { results: ArrayLike<{ [i: number]: { transcript: string } }> }) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn(() => this.onend?.());

  constructor() {
    FakeSpeechRecognition.instances.push(this);
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useSpeechRecognition", () => {
  it("reports UNAVAILABLE when the browser exposes no speech recognition API", () => {
    const { result } = renderHook(() => useSpeechRecognition());
    expect(result.current.state).toBe("UNAVAILABLE");
  });

  describe("when the browser supports SpeechRecognition", () => {
    beforeEach(() => {
      FakeSpeechRecognition.instances = [];
      vi.stubGlobal("SpeechRecognition", FakeSpeechRecognition);
    });

    it("starts in the IDLE state", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      expect(result.current.state).toBe("IDLE");
    });

    it("transitions to LISTENING and calls start() on the native API", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      act(() => result.current.start());
      expect(result.current.state).toBe("LISTENING");
      expect(FakeSpeechRecognition.instances[0].start).toHaveBeenCalledTimes(1);
    });

    it("produces a transcript and moves to RESULT when recognition succeeds", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      act(() => result.current.start());
      act(() => {
        FakeSpeechRecognition.instances[0].onresult?.({ results: [[{ transcript: "Why did my range drop?" }]] });
      });
      expect(result.current.state).toBe("RESULT");
      expect(result.current.transcript).toBe("Why did my range drop?");
    });

    it("surfaces a permission-denied message distinctly", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      act(() => result.current.start());
      act(() => {
        FakeSpeechRecognition.instances[0].onerror?.({ error: "not-allowed" });
      });
      expect(result.current.state).toBe("ERROR");
      expect(result.current.errorMessage).toMatch(/denied/i);
    });

    it("surfaces a generic error message for other recognition failures", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      act(() => result.current.start());
      act(() => {
        FakeSpeechRecognition.instances[0].onerror?.({ error: "network" });
      });
      expect(result.current.state).toBe("ERROR");
      expect(result.current.errorMessage).toMatch(/try again/i);
    });

    it("stop() invokes the native stop and returns to IDLE via onend", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      act(() => result.current.start());
      act(() => result.current.stop());
      expect(FakeSpeechRecognition.instances[0].stop).toHaveBeenCalledTimes(1);
      expect(result.current.state).toBe("IDLE");
    });

    it("reset() clears the transcript and error and returns to IDLE", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      act(() => result.current.start());
      act(() => {
        FakeSpeechRecognition.instances[0].onresult?.({ results: [[{ transcript: "hello" }]] });
      });
      act(() => result.current.reset());
      expect(result.current.state).toBe("IDLE");
      expect(result.current.transcript).toBe("");
      expect(result.current.errorMessage).toBeNull();
    });

    it("retry after an error starts a fresh recognition and clears the old error", () => {
      const { result } = renderHook(() => useSpeechRecognition());
      act(() => result.current.start());
      act(() => {
        FakeSpeechRecognition.instances[0].onerror?.({ error: "network" });
      });
      act(() => result.current.start());
      expect(result.current.state).toBe("LISTENING");
      expect(result.current.errorMessage).toBeNull();
      expect(FakeSpeechRecognition.instances).toHaveLength(2);
    });
  });
});
