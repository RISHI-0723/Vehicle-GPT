import { useState, type FormEvent } from "react";
import { Check, Copy } from "lucide-react";
import { intelligenceApi } from "../api/endpoints";
import { toApiError } from "../api/client";
import type { WhatIfResponse } from "../api/types";
import { Async } from "../components/Async";
import { RecommendationList } from "../components/intelligence";
import { Card, ErrorState, SectionHeading } from "../components/ui";
import { describeApiError } from "../lib/errors";
import { formatKm, formatKwh, formatPercent, formatSignedKm } from "../lib/format";
import { useResource } from "../lib/useResource";
import type { CanonicalDemo } from "../demo/canonical";
import { DEMO_VEHICLE_ID } from "../demo/config";
import { writeToClipboard } from "../office/clipboard";
import { formatWhatIfInsight } from "../office/insights";
import { buildHeroWhatIfRequest, type WhatIfChoice } from "./whatIfRequest";

type Phase =
  | { kind: "idle" }
  | { kind: "pending"; choice: WhatIfChoice }
  | { kind: "done"; result: WhatIfResponse }
  | { kind: "error"; message: string };

const CHOICES: Array<{ value: WhatIfChoice; label: string; cta: string; pendingText: string }> = [
  {
    value: "NORMAL_DRIVING",
    label: "Normal driving",
    cta: "What if I drove normally?",
    pendingText: "Comparing your drive with normal driving...",
  },
  {
    value: "FAST_CHARGING",
    label: "Simulated fast charging",
    cta: "What if I charged instead?",
    pendingText: "Comparing your drive with simulated charging...",
  },
];

export function WhatIf({ hero }: { hero: CanonicalDemo }) {
  const heroId = hero.aggressive.simulationId;
  const [choice, setChoice] = useState<WhatIfChoice>("NORMAL_DRIVING");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const recs = useResource(`recs:${heroId}`, () => intelligenceApi.recommendations(DEMO_VEHICLE_ID, heroId));
  const selected = CHOICES.find((c) => c.value === choice) ?? CHOICES[0];

  async function run(event: FormEvent) {
    event.preventDefault();
    setPhase({ kind: "pending", choice });
    try {
      const result = await intelligenceApi.whatIf(buildHeroWhatIfRequest(heroId, choice));
      setPhase({ kind: "done", result });
    } catch (err) {
      setPhase({ kind: "error", message: describeApiError(toApiError(err)) });
    }
  }

  const pendingChoice = CHOICES.find((c) => phase.kind === "pending" && c.value === phase.choice);

  return (
    <div className="page">
      <h1 className="page-title">What if I drove differently?</h1>
      <p className="muted">Compares this drive with the same starting conditions under another scenario.</p>

      <form className="card" onSubmit={run}>
        <fieldset className="choice-group">
          <legend>Compare with</legend>
          {CHOICES.map((c) => (
            <label key={c.value} className="choice">
              <input
                type="radio"
                name="whatif-scenario"
                value={c.value}
                checked={choice === c.value}
                onChange={() => setChoice(c.value)}
              />
              <span>{c.label}</span>
            </label>
          ))}
        </fieldset>
        <button type="submit" className="btn btn--primary btn--block" disabled={phase.kind === "pending"}>
          {selected.cta}
        </button>
      </form>

      {phase.kind === "pending" && pendingChoice ? (
        <section className="card simulating" role="status" aria-live="polite">
          <p className="eyebrow">SIMULATING</p>
          <p>{pendingChoice.pendingText}</p>
          <div className="progress" aria-hidden="true">
            <span />
          </div>
        </section>
      ) : null}

      {phase.kind === "error" ? <ErrorState message={phase.message} /> : null}

      {phase.kind === "done" ? <WhatIfResult result={phase.result} /> : null}

      <Async resource={recs} lines={3}>
        {(r) => (
          <Card labelledBy="whatif-recs">
            <SectionHeading id="whatif-recs">Recommendations</SectionHeading>
            <RecommendationList items={r.recommendations} />
          </Card>
        )}
      </Async>
    </div>
  );
}

function CopySimulationResultButton({ result }: { result: WhatIfResponse }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const ok = await writeToClipboard(formatWhatIfInsight(result));
    setCopied(ok);
    if (ok) setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button type="button" className="btn btn--ghost" onClick={() => void handleCopy()}>
      {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
      {copied ? "Copied" : "Copy simulation result"}
    </button>
  );
}

export function WhatIfResult({ result }: { result: WhatIfResponse }) {
  const yours = result.base_metrics.estimated_range_km;
  const other = result.counterfactual_metrics.estimated_range_km;
  const change = result.estimated_range_change_km;
  const isCharging = result.counterfactual_scenario === "FAST_CHARGING";

  return (
    <Card labelledBy="whatif-result" className="whatif-result">
      <SectionHeading id="whatif-result">Result</SectionHeading>
      <div className="compare">
        <div>
          <p className="eyebrow">Your drive</p>
          <p className="compare__value">{yours !== null ? formatKm(yours) : "–"}</p>
        </div>
        <div>
          <p className="eyebrow">{isCharging ? "Simulated charging" : "Normal driving"}</p>
          <p className="compare__value">
            {isCharging
              ? formatKwh(result.counterfactual_metrics.energy_consumed_kwh)
              : other !== null
                ? formatKm(other)
                : "–"}
          </p>
        </div>
      </div>

      {change !== null ? (
        <>
          <p className="potential">
            Potential difference: <strong>{formatSignedKm(change)}</strong>
          </p>
          <p className="muted small">Estimated potential, not a guaranteed saving.</p>
        </>
      ) : (
        <p className="muted">
          Range comparison is not applicable for charging sessions. Charging metrics are shown instead:
          energy {formatKwh(result.counterfactual_metrics.energy_consumed_kwh)}, ending charge{" "}
          {formatPercent(result.counterfactual_metrics.ending_soc_percent)}.
        </p>
      )}

      <p className="muted small">Starting charge {formatPercent(result.starting_soc_percent)}</p>
      <p className="muted small">{result.interpretation}</p>
      <p className="disclosure">
        <strong>DETERMINISTIC SIMULATION</strong> Estimated from the same starting conditions using a different scenario.
      </p>
      <CopySimulationResultButton result={result} />
    </Card>
  );
}
