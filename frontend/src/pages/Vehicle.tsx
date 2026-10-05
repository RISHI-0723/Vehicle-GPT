import { useState } from "react";
import { Download } from "lucide-react";
import { backendApi, intelligenceApi } from "../api/endpoints";
import { Async } from "../components/Async";
import { Card, MetricCard, SectionHeading } from "../components/ui";
import { DEMO_VEHICLE_ID } from "../demo/config";
import type { CanonicalDemo } from "../demo/canonical";
import type { DriveRecord } from "../demo/discovery";
import { useDemo } from "../demo/DemoContext";
import { anomalyCopy, formatKwh, formatPercent, stressCopy } from "../lib/format";
import { useResource } from "../lib/useResource";
import { downloadTextFile } from "../office/download";
import { buildDriveReportMarkdown, driveReportFilename } from "../office/exportReport";

export function Vehicle({ hero }: { hero: CanonicalDemo }) {
  const heroDrive: DriveRecord = hero.aggressive;
  const heroId = heroDrive.simulationId;
  const vehicle = useResource("vehicle", () => backendApi.vehicle(DEMO_VEHICLE_ID));
  const stress = useResource(`stress:${heroId}`, () => intelligenceApi.batteryStress(DEMO_VEHICLE_ID, heroId));
  const energy = useResource(`energy:${heroId}`, () => intelligenceApi.energy(DEMO_VEHICLE_ID, heroId));
  const anomaly = useResource(`anomaly:${heroId}`, () => intelligenceApi.anomaly(DEMO_VEHICLE_ID, heroId));
  const range = useResource(`range:${heroId}`, () => intelligenceApi.range(DEMO_VEHICLE_ID, heroId));
  const summary = useResource(`summary:${heroId}`, () => intelligenceApi.summary(DEMO_VEHICLE_ID, heroId));

  return (
    <div className="page">
      <h1 className="page-title">
        {vehicle.data ? `${vehicle.data.make} ${vehicle.data.model}` : "VehicleGPT EV Demo"}
      </h1>
      <p className="muted small">
        {vehicle.data
          ? `${vehicle.data.battery_type} battery · ${formatKwh(vehicle.data.usable_battery_capacity_kwh)} usable`
          : "Demo vehicle"}
      </p>

      <Card labelledBy="state-title">
        <SectionHeading id="state-title">Latest drive end state</SectionHeading>
        <div className="metric-grid">
          <MetricCard
            label="State of charge"
            value={heroDrive.endSocPercent !== null ? formatPercent(heroDrive.endSocPercent) : "–"}
            hint="Simulated, end of latest drive"
          />
          <MetricCard
            label="Battery temperature"
            value={heroDrive.endBatteryTemperatureC !== null ? `${heroDrive.endBatteryTemperatureC.toFixed(1)} °C` : "–"}
            hint="Simulated, end of latest drive"
          />
        </div>
      </Card>

      <Card labelledBy="stress-title" className="stress-card">
        <div id="battery-stress" />
        <SectionHeading id="stress-title">Battery operating stress</SectionHeading>
        <Async resource={stress} lines={3}>
          {(s) => (
            <>
              <p className="stress-level">{stressCopy(s.stress_level)}</p>
              <p className="muted small">Current operating stress. This is not battery health, degradation, or remaining life.</p>
              <p className="muted small">{s.explanation}</p>
            </>
          )}
        </Async>
      </Card>

      <Card labelledBy="eff-title">
        <SectionHeading id="eff-title">Energy efficiency</SectionHeading>
        <Async resource={energy} lines={3}>
          {(e) => (
            <>
              <p className="muted small">Rating: {e.rating}</p>
              <p className="muted small">{e.rating_reason}</p>
            </>
          )}
        </Async>
      </Card>

      <Card labelledBy="anomaly-title">
        <div id="anomaly" />
        <SectionHeading id="anomaly-title">Driving anomaly check</SectionHeading>
        <Async resource={anomaly} lines={3}>
          {(a) => (
            <>
              <p>{anomalyCopy(a.is_anomalous)}</p>
              {a.reasons.map((reason) => (
                <p key={reason} className="muted small">{reason}</p>
              ))}
            </>
          )}
        </Async>
      </Card>

      <Card labelledBy="range-conf-title">
        <SectionHeading id="range-conf-title">Range confidence</SectionHeading>
        <Async resource={range} lines={2}>
          {(r) => (
            <>
              <p>Confidence: {r.confidence}</p>
              <p className="muted small">{r.confidence_reason}</p>
            </>
          )}
        </Async>
      </Card>

      <Card labelledBy="truth-title">
        <SectionHeading id="truth-title">Data & connectivity</SectionHeading>
        <ul className="truth-list">
          <li>
            <span className="truth-list__label">Vehicle identity</span>
            <span className="truth-list__value">KNOWN — fixed demo configuration</span>
          </li>
          <li>
            <span className="truth-list__label">Drive and intelligence data</span>
            <span className="truth-list__value">SIMULATED — synthetic telemetry, not a real drive</span>
          </li>
          <li>
            <span className="truth-list__label">Physical vehicle connection</span>
            <span className="truth-list__value">UNAVAILABLE — not connected</span>
          </li>
        </ul>
      </Card>

      <Card labelledBy="export-title">
        <SectionHeading id="export-title">Export</SectionHeading>
        <p className="muted small">Download this drive's intelligence as a Markdown report.</p>
        <button
          type="button"
          className="btn btn--secondary btn--block"
          disabled={!vehicle.data || !summary.data}
          onClick={() => {
            if (!vehicle.data || !summary.data) return;
            downloadTextFile(
              driveReportFilename(heroDrive),
              buildDriveReportMarkdown({ vehicle: vehicle.data, drive: heroDrive, summary: summary.data }),
            );
          }}
        >
          <Download size={16} aria-hidden="true" /> Export drive report
        </button>
      </Card>

      <DemoControls />
    </div>
  );
}

function DemoControls() {
  const { resetDemo } = useDemo();
  const [confirming, setConfirming] = useState(false);

  return (
    <Card labelledBy="demo-controls" className="demo-controls">
      <SectionHeading id="demo-controls">Demo controls</SectionHeading>
      <p className="muted small">
        Developer and demo tool. Reset deletes all simulated drives for the demo vehicle. Prepare Demo then recreates the same deterministic data.
      </p>
      {confirming ? (
        <div className="confirm-row">
          <button type="button" className="btn btn--danger" onClick={() => void resetDemo()}>
            Confirm reset
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => setConfirming(false)}>
            Cancel
          </button>
        </div>
      ) : (
        <button type="button" className="btn btn--secondary btn--block" onClick={() => setConfirming(true)}>
          Reset Demo
        </button>
      )}
    </Card>
  );
}
