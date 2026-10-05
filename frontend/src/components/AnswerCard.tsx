import { useState } from "react";
import { Link } from "react-router-dom";
import { Share2 } from "lucide-react";
import type { ActionItem, AskResponse, EvidenceItem } from "../api/types";
import { actionPath } from "../ai/actions";
import { shareText } from "../office/share";
import { Card, ConfidenceNote, SectionHeading } from "./ui";

function ShareAnswerButton({ response }: { response: AskResponse }) {
  const [status, setStatus] = useState<"idle" | "shared" | "copied" | "unavailable">("idle");

  async function handleShare() {
    const outcome = await shareText("VehicleGPT answer", response.answer);
    if (outcome === "cancelled") return;
    setStatus(outcome === "shared" ? "shared" : outcome === "copied" ? "copied" : "unavailable");
    setTimeout(() => setStatus("idle"), 2000);
  }

  return (
    <div>
      <button type="button" className="btn btn--ghost" onClick={() => void handleShare()}>
        <Share2 size={16} aria-hidden="true" /> Share
      </button>
      {status === "copied" ? <p className="muted small" role="status">Copied to clipboard</p> : null}
      {status === "unavailable" ? <p className="muted small" role="status">Sharing isn't available here</p> : null}
    </div>
  );
}

export function EvidenceList({ items }: { items: EvidenceItem[] }) {
  if (items.length === 0) return null;
  return (
    <ul className="evidence-list" aria-label="Evidence">
      {items.map((item) => (
        <li key={item.id} className="evidence-item">
          <span className="evidence-item__label">{item.label}</span>
          {item.value !== null && item.value !== undefined ? (
            <span className="evidence-item__value">
              {item.value}
              {item.unit ? ` ${item.unit}` : ""}
            </span>
          ) : null}
          {item.comparison ? <span className="evidence-item__comparison">{item.comparison}</span> : null}
        </li>
      ))}
    </ul>
  );
}

export function ActionList({ actions }: { actions: ActionItem[] }) {
  if (actions.length === 0) return null;
  return (
    <div className="action-list">
      {actions.map((action) => (
        <Link key={action.id} className="btn btn--secondary" to={actionPath(action)}>
          {action.label}
        </Link>
      ))}
    </div>
  );
}

/** Renders one AI answer: text, confidence, evidence, actions, and the
 * simulation disclosure the AI must never contradict. */
export function AnswerCard({ response }: { response: AskResponse }) {
  return (
    <Card labelledBy="answer-title" className="answer-card">
      <SectionHeading id="answer-title">Answer</SectionHeading>
      <p className="answer-card__text">{response.answer}</p>
      <ConfidenceNote level={response.confidence} />
      {response.fallback_used ? (
        <p className="muted small answer-card__fallback" role="status">
          Showing a deterministic explanation — the AI assistant was unavailable.
        </p>
      ) : null}
      <p className="muted small answer-card__disclosure">
        Based on synthetic simulated telemetry, not live vehicle data.
      </p>
      <EvidenceList items={response.evidence} />
      <ActionList actions={response.actions} />
      <ShareAnswerButton response={response} />
    </Card>
  );
}
