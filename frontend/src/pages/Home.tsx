import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { intelligenceApi } from "../api/endpoints";
import { Async } from "../components/Async";
import { RangeCard, RecommendationList } from "../components/intelligence";
import { Card, MetricCard, SectionHeading } from "../components/ui";
import { useResource } from "../lib/useResource";
import { anomalyCopy, formatKwh, formatMinutes, scenarioLabel, stressCopy } from "../lib/format";
import { DEMO_VEHICLE_ID } from "../demo/config";
import type { CanonicalDemo } from "../demo/canonical";
import type { DriveRecord } from "../demo/discovery";

export function Home({ hero, drives }: { hero: CanonicalDemo; drives: DriveRecord[] }) {
  const heroDrive: DriveRecord = hero.aggressive;
  const heroId = heroDrive.simulationId;
  const normalId = hero.normal.simulationId;

  const summary = useResource(`summary:${heroId}`, () => intelligenceApi.summary(DEMO_VEHICLE_ID, heroId));
  const heroRange = useResource(`range:${heroId}`, () => intelligenceApi.range(DEMO_VEHICLE_ID, heroId));
  const normalRange = useResource(`range:${normalId}`, () => intelligenceApi.range(DEMO_VEHICLE_ID, normalId));

  return (
    <div className="page page--home">
      <p className="status-line" role="status">
        Demo ready · {drives.length} persisted simulated {drives.length === 1 ? "drive" : "drives"}
      </p>

      <Card className="drive-card" labelledBy="latest-drive-title">
        <p className="eyebrow" id="latest-drive-title">Latest drive</p>
        <p className="drive-card__title">{scenarioLabel(heroDrive.scenario)}</p>
        <p className="muted small">{formatMinutes(heroDrive.durationMinutes)} · Simulation mode</p>
      </Card>

      <Async resource={heroRange} lines={4}>
        {(range) => <RangeCard range={range} normalRange={normalRange.data} />}
      </Async>

      <Async resource={summary} lines={4}>
        {(s) => (
          <>
            <Card labelledBy="explain-title">
              <SectionHeading id="explain-title">What happened</SectionHeading>
              <p className="explain-headline">{s.explanation.headline}</p>
              <p className="muted">{s.explanation.summary}</p>
            </Card>

            <Card labelledBy="key-title">
              <SectionHeading id="key-title">Key intelligence</SectionHeading>
              <div className="metric-grid">
                <MetricCard label="Energy used" value={formatKwh(s.energy.energy_consumed_kwh)} />
                <MetricCard label="Regenerated" value={formatKwh(s.energy.energy_regenerated_kwh)} />
                <MetricCard
                  label="Operating stress"
                  value={stressCopy(s.battery_stress.stress_level)}
                  hint="Current operating stress, not battery health"
                />
              </div>
              <p className="muted small">{anomalyCopy(s.anomaly.is_anomalous)}</p>
            </Card>

            <Card labelledBy="rec-title">
              <SectionHeading id="rec-title">Top recommendation</SectionHeading>
              <RecommendationList items={s.recommendations.recommendations.slice(0, 1)} />
            </Card>
          </>
        )}
      </Async>

      <Link className="btn btn--primary btn--block home-cta" to="/what-if">
        What if I drove normally? <ChevronRight size={18} aria-hidden="true" />
      </Link>

      <Link
        className="btn btn--secondary btn--block home-ask-cta"
        to={`/ask?q=${encodeURIComponent("Why did my range drop?")}`}
      >
        Ask your vehicle: "Why did my range drop?" <ChevronRight size={18} aria-hidden="true" />
      </Link>
    </div>
  );
}
