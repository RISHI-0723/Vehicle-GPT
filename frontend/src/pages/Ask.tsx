import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, Mic, MicOff } from "lucide-react";
import { aiApi } from "../api/endpoints";
import { toApiError } from "../api/client";
import type { AskResponse, ConversationMessage } from "../api/types";
import { appendExchange } from "../ai/conversation";
import { SUGGESTED_PROMPTS } from "../ask/intents";
import { AnswerCard } from "../components/AnswerCard";
import { ScanVehicle } from "../components/ScanVehicle";
import { ErrorState, LoadingSkeleton } from "../components/ui";
import { DEMO_VEHICLE_ID } from "../demo/config";
import { describeApiError } from "../lib/errors";
import { VOICE_UNAVAILABLE_COPY, useSpeechRecognition } from "../voice/useSpeechRecognition";

type Phase = "idle" | "asking" | "done" | "error";

export function Ask() {
  const inputId = useId();
  const [searchParams] = useSearchParams();
  const [text, setText] = useState(() => searchParams.get("q") ?? "");
  const [phase, setPhase] = useState<Phase>("idle");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const voice = useSpeechRecognition();
  const autoAsked = useRef(false);

  // Sync a finished voice transcript into the input during render (rather than
  // in an effect) so it takes effect in the same commit, without an extra pass.
  const [appliedTranscript, setAppliedTranscript] = useState<string | null>(null);
  if (voice.state === "RESULT" && voice.transcript && voice.transcript !== appliedTranscript) {
    setAppliedTranscript(voice.transcript);
    setText(voice.transcript);
  }

  async function ask(question: string, history: ConversationMessage[]) {
    setPhase("asking");
    setErrorMessage(null);
    try {
      const result = await aiApi.ask({ vehicle_id: DEMO_VEHICLE_ID, question, conversation: history });
      setResponse(result);
      setConversation((prev) => appendExchange(prev, question, result.answer));
      setPhase("done");
    } catch (err) {
      setErrorMessage(describeApiError(toApiError(err)));
      setPhase("error");
    }
  }

  // A prefilled question (e.g. from Home's "Ask your vehicle" or Drive's AI
  // actions) is asked automatically once, so tapping it goes straight to an answer.
  useEffect(() => {
    const prefilled = searchParams.get("q");
    if (prefilled && !autoAsked.current) {
      autoAsked.current = true;
      void ask(prefilled, []);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    const question = text.trim();
    if (!question || phase === "asking") return;
    void ask(question, conversation);
  }

  function toggleVoice() {
    if (voice.state === "LISTENING") {
      voice.stop();
    } else {
      voice.start();
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">Ask VehicleGPT</h1>
      <p className="muted small">
        Ask a question in your own words. Answers are explained from real vehicle intelligence --
        never invented.
      </p>

      <form className="card" onSubmit={submit}>
        <label htmlFor={inputId} className="field-label">
          Ask about your vehicle
        </label>
        <div className="ask-input-row">
          <input
            id={inputId}
            className="field"
            type="text"
            value={text}
            placeholder="e.g. Why did my range drop?"
            onChange={(e) => setText(e.target.value)}
          />
          <button
            type="button"
            className="btn btn--ghost mic-btn"
            onClick={toggleVoice}
            disabled={voice.state === "UNAVAILABLE"}
            aria-label={voice.state === "LISTENING" ? "Stop listening" : "Ask by voice"}
            aria-pressed={voice.state === "LISTENING"}
          >
            {voice.state === "LISTENING" ? (
              <MicOff size={18} aria-hidden="true" />
            ) : (
              <Mic size={18} aria-hidden="true" />
            )}
          </button>
        </div>
        {voice.state === "LISTENING" ? (
          <p role="status" className="muted small">
            Listening…
          </p>
        ) : null}
        {voice.state === "UNAVAILABLE" ? <p className="muted small">{VOICE_UNAVAILABLE_COPY}</p> : null}
        {voice.state === "ERROR" && voice.errorMessage ? (
          <p role="alert" className="muted small">
            {voice.errorMessage}
          </p>
        ) : null}
        <button type="submit" className="btn btn--primary btn--block" disabled={phase === "asking"}>
          {phase === "asking" ? "Thinking…" : "Ask"}
        </button>
      </form>

      <ScanVehicle />

      {phase === "asking" ? <LoadingSkeleton lines={3} label="Thinking" /> : null}
      {phase === "error" && errorMessage ? <ErrorState message={errorMessage} /> : null}
      {phase === "done" && response ? <AnswerCard response={response} /> : null}

      {conversation.length > 0 ? (
        <section aria-labelledby="recent-title">
          <h2 id="recent-title" className="section-heading">
            Recent conversation
          </h2>
          <ul className="conversation-list">
            {conversation.map((message, index) => (
              <li key={index} className={`conversation-item conversation-item--${message.role}`}>
                <span className="conversation-item__role">{message.role === "user" ? "You" : "VehicleGPT"}</span>
                <span>{message.content}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="suggest-title">
        <h2 id="suggest-title" className="section-heading">
          Suggested questions
        </h2>
        <ul className="prompt-list">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <li key={prompt.intent}>
              <Link className="prompt" to={prompt.path}>
                <span>{prompt.label}</span>
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
