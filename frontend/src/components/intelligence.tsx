import { ArrowDown } from "lucide-react";
import { Link } from "react-router-dom";
import type { Contributor, Recommendation, RangeEstimation } from "../api/types";
import { formatKm, impactCopy } from "../lib/format";
import { ConfidenceNote } from "./ui";

interface RangeCardProps {
  range: RangeEstimation;
  /** Range of the NORMAL_DRIVING comparison drive, when the backend provides it. */
  normalRange: RangeEstimation | null;
}

/** Shows the backend estimate and, only when both values are valid, the difference from normal. */
export function RangeCard({ range, normalRange }: RangeCardProps) {
  const current = range.estimated_range_km;
  const normal = normalRange?.estimated_range_km ?? null;
  const gap = current !== null && normal !== null ? normal - current : null;

  return (
    <section className="card card--hero" aria-labelledby="range-title">
      <p id="range-title" className="eyebrow">Estimated range</p>
      {current !== null ? (
        <p className="range-value" aria-label={`Estimated range ${formatKm(current)}`}>
          <span className="range-value__number">{Math.round(current)}</span>
          <span className="range-value__unit">km</span>
        </p>
      ) : (
        <p className="range-empty">Range is unavailable for this drive.</p>
      )}
      {gap !== null && gap > 0 ? (
        <p className="range-gap">
          <ArrowDown size={18} aria-hidden="true" />
          <span>{Math.round(gap)} km vs normal</span>
        </p>
      ) : null}
      <ConfidenceNote level={range.confidence} />
      <Link className="btn btn--primary btn--block" to="/why-range">
        Why did my range change?
      </Link>
    </section>
  );
}

export function ContributorBars({ contributors }: { contributors: Contributor[] }) {
  if (contributors.length === 0) {
    return <p className="muted">No contributor data is available for this drive.</p>;
  }
  return (
    <ul className="contributors" aria-label="Main contributors">
      {contributors.map((c) => (
        <li key={c.id} className="contributor">
          <div className="contributor__head">
            <span className="contributor__name">{c.name}</span>
            <span className="contributor__impact">
              {c.is_available ? impactCopy(c.impact_level) : "No baseline comparison"}
            </span>
          </div>
          <div
            className="bar"
            role="meter"
            aria-label={`${c.name} impact score`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(c.impact_score)}
          >
            <span className="bar__fill" style={{ width: `${Math.min(100, Math.max(0, c.impact_score))}%` }} />
          </div>
          <p className="contributor__desc">{c.description}</p>
        </li>
      ))}
    </ul>
  );
}

export function RecommendationList({ items }: { items: Recommendation[] }) {
  const shown = items.slice(0, 5);
  if (shown.length === 0) {
    return <p className="muted">No recommendations for this drive.</p>;
  }
  return (
    <ol className="recs">
      {shown.map((r) => (
        <li key={r.id} className={`rec rec--${r.priority.toLowerCase()}`}>
          <div className="rec__head">
            <span className="rec__priority">{r.priority}</span>
            <h3 className="rec__title">{r.title}</h3>
          </div>
          <p className="rec__reason">{r.reason}</p>
          <p className="rec__benefit">{r.expected_benefit}</p>
        </li>
      ))}
    </ol>
  );
}
