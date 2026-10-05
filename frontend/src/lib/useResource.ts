import { useCallback, useEffect, useRef, useState } from "react";
import { toApiError, type ApiError } from "../api/client";

// In-memory last-good responses. Used only to show "last available data" during a
// network loss. Never persisted, and never presented as live.
const lastGood = new Map<string, unknown>();

export function clearResourceCache(): void {
  lastGood.clear();
}

interface ResourceState<T> {
  key: string | null;
  data: T | null;
  error: ApiError | null;
  stale: boolean;
}

export interface Resource<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  /** True when `data` is the last successful response and the network is currently failing. */
  stale: boolean;
  retry: () => void;
}

export function useResource<T>(key: string | null, load: () => Promise<T>): Resource<T> {
  const [state, setState] = useState<ResourceState<T>>(() => ({
    key,
    data: key !== null ? (lastGood.get(key) as T | undefined) ?? null : null,
    error: null,
    stale: false,
  }));
  const [attempt, setAttempt] = useState(0);
  const loadRef = useRef(load);

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    if (key === null) return;
    let cancelled = false;
    loadRef
      .current()
      .then((data) => {
        if (cancelled) return;
        lastGood.set(key, data);
        setState({ key, data, error: null, stale: false });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const apiError = toApiError(err);
        const cached = (lastGood.get(key) as T | undefined) ?? null;
        setState({
          key,
          data: cached,
          error: apiError,
          stale: cached !== null && apiError.kind !== "http",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [key, attempt]);

  const retry = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
    setAttempt((n) => n + 1);
  }, []);

  const matchesKey = state.key === key;
  const data = matchesKey ? state.data : null;
  const error = matchesKey ? state.error : null;
  return {
    data,
    error,
    loading: key !== null && !matchesKey ? true : key !== null && data === null && error === null,
    stale: matchesKey ? state.stale : false,
    retry,
  };
}
