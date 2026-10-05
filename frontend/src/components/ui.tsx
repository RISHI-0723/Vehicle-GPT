import type { ReactNode } from "react";
import { Info, RefreshCw, WifiOff } from "lucide-react";
import type { BaselineMatchType, ConfidenceLevel } from "../api/types";
import { baselineCopy, confidenceCopy } from "../lib/format";

export function SimulationBadge() {
  return (
    <div className="sim-badge" role="note">
      <span className="sim-badge__chip">SIMULATION MODE</span>
      <span className="sim-badge__text">DEMO VEHICLE · SYNTHETIC TELEMETRY</span>
    </div>
  );
}

export function Card({ children, className = "", as = "section", labelledBy }: {
  children: ReactNode;
  className?: string;
  as?: "section" | "article" | "div";
  labelledBy?: string;
}) {
  const Tag = as;
  return (
    <Tag className={`card ${className}`} aria-labelledby={labelledBy}>
      {children}
    </Tag>
  );
}

export function SectionHeading({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <h2 id={id} className="section-heading">
      {children}
    </h2>
  );
}

export function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="metric">
      <span className="metric__label">{label}</span>
      <span className="metric__value">{value}</span>
      {hint ? <span className="metric__hint">{hint}</span> : null}
    </div>
  );
}

export function BaselineNote({ match }: { match: BaselineMatchType }) {
  return (
    <p className={`baseline-note baseline-note--${match.toLowerCase()}`}>
      <Info size={16} aria-hidden="true" />
      <span>{baselineCopy(match)}</span>
    </p>
  );
}

export function ConfidenceNote({ level }: { level: ConfidenceLevel }) {
  const copy = confidenceCopy(level);
  if (!copy) return null;
  return <p className="confidence-note">{copy}</p>;
}

export function LoadingSkeleton({ lines = 3, label = "Loading" }: { lines?: number; label?: string }) {
  return (
    <div className="skeleton" role="status" aria-label={label}>
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className="skeleton__line" style={{ width: `${92 - i * 14}%` }} />
      ))}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state--error" role="alert">
      <WifiOff size={20} aria-hidden="true" />
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="btn btn--secondary" onClick={onRetry}>
          <RefreshCw size={16} aria-hidden="true" /> Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, body, children }: { title: string; body?: string; children?: ReactNode }) {
  return (
    <div className="state">
      <h3>{title}</h3>
      {body ? <p>{body}</p> : null}
      {children}
    </div>
  );
}

export function StaleBanner({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="stale-banner" role="status">
      <span>Connection lost · Showing last available data</span>
      <button type="button" className="btn btn--ghost" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
