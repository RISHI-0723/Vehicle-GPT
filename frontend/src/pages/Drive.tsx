import { Link } from "react-router-dom";
import { intelligenceApi } from "../api/endpoints";
import { Async } from "../components/Async";
import { RecommendationList } from "../components/intelligence";
import { Card, MetricCard, SectionHeading } from "../components/ui";
import { DEMO_VEHICLE_ID } from "../demo/config";
import type { CanonicalDemo } from "../demo/canonical";
import type { DriveRecord } from "../demo/discovery";
import { anomalyCopy, formatKm, formatKwh, formatMinutes, scenarioLabel, stressCopy } from "../lib/format";
import { useResource } from "../lib/useResource";

export function Drive({ hero, drives }: { hero: CanonicalDemo; drives: DriveRecord[] }) {
  const heroDrive = hero.aggressive;
  const heroId = heroDrive.simulationId;
  const summary = useResource(`summary:${heroId}`, () => intelligenceApi.summary(DEMO_VEHICLE_ID, heroId));
  const recent = orderRecent(drives, heroId).slice(0, 5);

  return (
    <div className="page">
      <h1 className="page-title">Latest completed drive</h1>
      <p className="muted small">
        A completed simulation, not live telemetry. There is no real-time speed, SOC, or location here.
      </p>

      <Card labelledBy="drive-summary">
        <SectionHeading id="drive-summary">{scenarioLabel(heroDrive.scenario)}</SectionHeading>
        <p className="muted small">{formatMinutes(heroDrive.durationMinutes)} · Simulation mode</p>
      </Card>

      <Async resource={summary} lines={5}>
        {(s) => (
          <>
            <Card labelledBy="drive-metrics">
              <SectionHeading id="drive-metrics">Energy</SectionHeading>
              <div className="metric-grid">
                <MetricCard label="Energy consumed" value={formatKwh(s.energy.energy_consumed_kwh)} />
                <MetricCard label="Energy regenerated" value={formatKwh(s.energy.energy_regenerated_kwh)} />
                <MetricCard label="Net energy" value={formatKwh(s.energy.net_energy_kwh)} />
                <MetricCard label="Distance" value={formatKm(s.energy.distance_km)} />
              </div>
              <p className="muted small">{s.energy.rating_reason}</p>
            </Card>

            <Card labelledBy="drive-range">
              <SectionHeading id="drive-range">Range and condition</SectionHeading>
              <div className="metric-grid">
                <MetricCard
                  label="Estimated range"
                  value={s.range_estimate.estimated_range_km !== null ? formatKm(s.range_estimate.estimated_range_km) : "Unavailable"}
                />
                <MetricCard label="Operating stress" value={stressCopy(s.battery_stress.stress_level)} />
              </div>
              <p className="muted small">{anomalyCopy(s.anomaly.is_anomalous)}</p>
            </Card>

            <Card labelledBy="drive-recs">
              <SectionHeading id="drive-recs">Recommendation</SectionHeading>
              <RecommendationList items={s.recommendations.recommendations.slice(0, 1)} />
            </Card>
          </>
        )}
      </Async>

      <Card labelledBy="recent-title">
        <SectionHeading id="recent-title">Recent drives</SectionHeading>
        <ul className="recent-list">
          {recent.map((d) => (
            <li key={d.simulationId} className="recent-list__item">
              <span>{scenarioLabel(d.scenario)}</span>
              <span className="muted small">{formatMinutes(d.durationMinutes)}</span>
            </li>
          ))}
        </ul>
      </Card>

      <details className="card calc">
        <summary>How this was calculated</summary>
        <ul className="muted small">
          <li>Samples recorded: {heroDrive.sampleCount}, every {heroDrive.stepSeconds ?? "–"} seconds.</li>
          <li>Comparison: values come from backend analysis of persisted simulated telemetry.</li>
          <li>Simulation ID: <code>{heroId}</code></li>
        </ul>
      </details>

      <Card labelledBy="ai-actions-title">
        <SectionHeading id="ai-actions-title">Ask about this drive</SectionHeading>
        <div className="action-list">
          <Link className="btn btn--secondary" to={`/ask?q=${encodeURIComponent("Why did my range drop?")}`}>
            Explain this drive
          </Link>
          <Link className="btn btn--secondary" to={`/ask?q=${encodeURIComponent("Was this worse than normal?")}`}>
            Compare with normal
          </Link>
          <Link className="btn btn--secondary" to={`/ask?q=${encodeURIComponent("What should I change?")}`}>
            What would improve this?
          </Link>
        </div>
      </Card>
    </div>
  );
}

/** Hero drive first, then the others, newest persisted first. */
export function orderRecent(drives: DriveRecord[], heroId: string): DriveRecord[] {
  return [...drives].sort((a, b) => {
    if (a.simulationId === heroId) return -1;
    if (b.simulationId === heroId) return 1;
    return Date.parse(b.startTime) - Date.parse(a.startTime);
  });
}
