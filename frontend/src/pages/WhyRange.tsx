import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, ChevronRight, Copy } from "lucide-react";
import { intelligenceApi } from "../api/endpoints";
import type { WhyRangeDropped } from "../api/types";
import { Async } from "../components/Async";
import { ContributorBars, RecommendationList } from "../components/intelligence";
import { BaselineNote, Card, ConfidenceNote, SectionHeading } from "../components/ui";
import { DEMO_VEHICLE_ID } from "../demo/config";
import type { CanonicalDemo } from "../demo/canonical";
import { useResource } from "../lib/useResource";
import { writeToClipboard } from "../office/clipboard";
import { formatRangeInsight } from "../office/insights";

function CopyInsightButton({ why }: { why: WhyRangeDropped }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const text = formatRangeInsight({
      estimatedRangeKm: why.range_estimate.estimated_range_km,
      contributors: why.contributors.contributors,
      topRecommendation: why.recommendations.recommendations[0] ?? null,
    });
    const ok = await writeToClipboard(text);
    setCopied(ok);
    if (ok) setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button type="button" className="btn btn--ghost" onClick={() => void handleCopy()}>
      {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
      {copied ? "Copied" : "Copy insight"}
    </button>
  );
}

export function WhyRange({ hero }: { hero: CanonicalDemo }) {
  const heroId = hero.aggressive.simulationId;
  const why = useResource(`why:${heroId}`, () => intelligenceApi.whyRangeDropped(DEMO_VEHICLE_ID, heroId));
  const contributors = useResource(`contributors:${heroId}`, () =>
    intelligenceApi.contributors(DEMO_VEHICLE_ID, heroId),
  );

  return (
    <div className="page">
      <h1 className="page-title">Why your range changed</h1>

      <Async resource={why} lines={5}>
        {(w) => (
          <>
            <Card labelledBy="why-headline">
              <p id="why-headline" className="explain-headline">{w.explanation.headline}</p>
              <p className="muted">{w.explanation.summary}</p>
              <BaselineNote match={w.baseline_match_type} />
              <ConfidenceNote level={w.confidence} />
              <CopyInsightButton why={w} />
            </Card>

            {w.explanation.key_factors.length > 0 ? (
              <Card labelledBy="factors-title">
                <SectionHeading id="factors-title">Key factors</SectionHeading>
                <ul className="factor-list">
                  {w.explanation.key_factors.map((factor) => (
                    <li key={factor}>{factor}</li>
                  ))}
                </ul>
              </Card>
            ) : null}
          </>
        )}
      </Async>

      <Card labelledBy="contrib-title">
        <SectionHeading id="contrib-title">Main contributors</SectionHeading>
        <Async resource={contributors} lines={4}>
          {(c) => (
            <>
              <BaselineNote match={c.baseline_match_type} />
              <ContributorBars contributors={c.contributors} />
            </>
          )}
        </Async>
      </Card>

      <Async resource={why} lines={3}>
        {(w) => (
          <Card labelledBy="why-recs">
            <SectionHeading id="why-recs">Recommendations</SectionHeading>
            <RecommendationList items={w.recommendations.recommendations} />
          </Card>
        )}
      </Async>

      <Link className="btn btn--primary btn--block" to="/what-if">
        What if I drove normally? <ChevronRight size={18} aria-hidden="true" />
      </Link>
    </div>
  );
}
