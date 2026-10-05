import { Database, ShieldCheck } from "lucide-react";
import { useDemo } from "../demo/DemoContext";
import { LoadingSkeleton, SimulationBadge } from "../components/ui";

/** Shown only when canonical demo data is absent. It never runs automatically. */
export function DemoSetup() {
  const { status, message, prepare, recheck } = useDemo();
  const preparing = status === "preparing";

  return (
    <div className="setup">
      <div className="setup__card">
        <p className="brand">VehicleGPT</p>
        <h1 className="setup__title">Your demo vehicle is ready to prepare.</h1>
        <p className="setup__body">
          VehicleGPT EV Demo uses deterministic synthetic telemetry. It is a simulation, not a
          connection to a real vehicle.
        </p>
        <SimulationBadge />

        {status === "checking" ? <LoadingSkeleton lines={2} label="Checking demo data" /> : null}

        {status === "setup" || preparing ? (
          <div className="setup__actions">
            <button
              type="button"
              className="btn btn--primary btn--block"
              onClick={prepare}
              disabled={preparing}
              aria-busy={preparing}
            >
              <Database size={18} aria-hidden="true" />
              {preparing ? "Preparing demo…" : "Prepare Demo"}
            </button>
            <p className="muted small">
              <ShieldCheck size={14} aria-hidden="true" /> Creates two simulated drives with fixed
              settings. Preparing again never duplicates them.
            </p>
          </div>
        ) : null}

        {status === "error" ? (
          <div className="state state--error" role="alert">
            <p>{message ?? "Vehicle intelligence is temporarily unavailable."}</p>
            <button type="button" className="btn btn--secondary btn--block" onClick={recheck}>
              Retry
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
