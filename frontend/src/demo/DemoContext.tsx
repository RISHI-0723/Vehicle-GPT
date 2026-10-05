import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { backendApi } from "../api/endpoints";
import { toApiError } from "../api/client";
import { CANONICAL_DEMO } from "./config";
import { discoverDrives, type DriveRecord } from "./discovery";
import {
  DemoPreparationError,
  prepareCanonicalDemo,
  resetCanonicalDemo,
  resolveCanonicalDemo,
  type CanonicalDemo,
} from "./canonical";

export type DemoStatus = "checking" | "setup" | "preparing" | "ready" | "error";

export interface DemoState {
  status: DemoStatus;
  /** Safe, user-facing message. Never a raw backend body. */
  message: string | null;
  hero: CanonicalDemo | null;
  drives: DriveRecord[];
  prepare: () => void;
  resetDemo: () => Promise<void>;
  recheck: () => void;
}

const DemoContext = createContext<DemoState | null>(null);

// Module-level guard so repeated taps (or StrictMode double effects) share one preparation.
let pendingPreparation: Promise<CanonicalDemo> | null = null;

function runPreparation(): Promise<CanonicalDemo> {
  if (!pendingPreparation) {
    const vehicleId = CANONICAL_DEMO.vehicleId;
    pendingPreparation = prepareCanonicalDemo({
      discover: () => discoverDrives(vehicleId),
      run: (request) => backendApi.runSimulation(request),
    }).finally(() => {
      pendingPreparation = null;
    });
  }
  return pendingPreparation;
}

function messageFor(err: unknown): string {
  if (err instanceof DemoPreparationError) return err.message;
  const apiError = toApiError(err);
  if (apiError.kind === "http" && apiError.status === 409) {
    return "A simulation is already running. Try again in a moment.";
  }
  return "Vehicle intelligence is temporarily unavailable.";
}

export function DemoProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<DemoStatus>("checking");
  const [message, setMessage] = useState<string | null>(null);
  const [hero, setHero] = useState<CanonicalDemo | null>(null);
  const [drives, setDrives] = useState<DriveRecord[]>([]);
  const [checkToken, setCheckToken] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // Read-only readiness check: discovers persisted data and never creates anything.
  useEffect(() => {
    let cancelled = false;
    discoverDrives(CANONICAL_DEMO.vehicleId)
      .then((found) => {
        if (cancelled) return;
        setDrives(found);
        const demo = resolveFromDrives(found);
        if (demo) {
          setHero(demo);
          setStatus("ready");
        } else {
          setHero(null);
          setStatus("setup");
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setMessage(messageFor(err));
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [checkToken]);

  const prepare = useCallback(() => {
    setStatus("preparing");
    setMessage(null);
    runPreparation()
      .then(async (demo) => {
        if (!mounted.current) return;
        setHero(demo);
        setDrives(await discoverDrives(CANONICAL_DEMO.vehicleId));
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (!mounted.current) return;
        setMessage(messageFor(err));
        setStatus("error");
      });
  }, []);

  const resetDemo = useCallback(async () => {
    setMessage(null);
    try {
      await resetCanonicalDemo();
      setHero(null);
      setDrives([]);
      setStatus("setup");
    } catch (err) {
      setMessage(messageFor(err));
      setStatus("error");
    }
  }, []);

  const recheck = useCallback(() => {
    setStatus("checking");
    setMessage(null);
    setCheckToken((n) => n + 1);
  }, []);

  const value = useMemo<DemoState>(
    () => ({ status, message, hero, drives, prepare, resetDemo, recheck }),
    [status, message, hero, drives, prepare, resetDemo, recheck],
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

function resolveFromDrives(found: DriveRecord[]): CanonicalDemo | null {
  const resolution = resolveCanonicalDemo(found);
  return resolution.ready ? { normal: resolution.normal!, aggressive: resolution.aggressive! } : null;
}

export function useDemo(): DemoState {
  const value = useContext(DemoContext);
  if (!value) throw new Error("useDemo must be used inside DemoProvider");
  return value;
}
