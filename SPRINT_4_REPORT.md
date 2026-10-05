# VehicleGPT — Sprint 4 Report

## 1. Executive Summary

Sprint 4 adds a local-LLM explanation layer (Ollama + llama3.1:8b) and
phone-native features (voice, camera, Office Kit) on top of the Sprint 1/2
deterministic engine and the Sprint 3 phone UI, without changing any Sprint
1/2 formula or Sprint 3 route. The product remains fully functional with
Ollama absent: every AI-routed question still gets a correct, evidence-based
answer via a deterministic fallback formatter.

All 216 Sprint 1–3 tests remain green. Sprint 4 adds 72 new backend (pytest)
tests and 73 new frontend (Vitest) tests — 145 new tests, well over the
40-test minimum. Total automated tests: **361 passing**.

## 2. Sprint 4 Goals

- Server-side AI explanation layer calling a local Ollama model
- Deterministic intent routing independent of the LLM
- Strict grounding: the LLM explains evidence, never invents or recalculates it
- Graceful, automatic deterministic fallback when the LLM is unavailable
- Bounded multi-turn conversation with a backend-owned system prompt
- Voice input (Web Speech API), camera capture (getUserMedia), and a real
  Office Kit workflow (copy/export/share)
- No regression to Sprint 1–3 behavior or tests

## 3. Architecture

```
SIMULATED VEHICLE DATA (Sprint 1)
        |
DETERMINISTIC VEHICLE INTELLIGENCE (Sprint 2: app/intelligence/*)
        |
DETERMINISTIC INTENT ROUTING (Sprint 4: app/ai/intent_router.py)
        |
LOCAL AI LANGUAGE REASONING (Sprint 4: app/ai/service.py -> Ollama)
        |
PHONE EXPERIENCE (Sprint 3 UI + Sprint 4 Ask/voice/camera/office kit)
```

New backend package: `backend/app/ai/` (config, schemas, intent_router,
conversation, system_prompt, ollama_client, intelligence_bridge, evidence,
fallback, response_validator, service) plus `backend/app/api/routes_ai.py`
(`POST /api/v1/ai/ask`), wired into `app/main.py`.

New frontend modules: `frontend/src/ai/` (types live in `src/api/types.ts`,
conversation bounding, action routing), `src/voice/useSpeechRecognition.ts`,
`src/camera/useCamera.ts`, `src/office/*` (clipboard, share, download,
insights, exportReport), `src/components/AnswerCard.tsx`,
`src/components/ScanVehicle.tsx`, plus upgrades to `Ask.tsx`, `Home.tsx`,
`Drive.tsx`, `Vehicle.tsx`, `WhyRange.tsx`, `WhatIf.tsx`.

## 4. AI Provider

Provider: **Ollama**, model: **llama3.1:8b**, running locally. Configured via
`AI_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `AI_TIMEOUT_SECONDS` in
`.env` (see `.env.example`). No API key or secret is needed or stored.

Manual verification on this machine: a local Ollama instance was reachable at
`http://127.0.0.1:11434`, but only `qwen2.5vl:3b` was pulled, not
`llama3.1:8b`. Live `/api/chat` calls against the configured model therefore
return an HTTP error from Ollama, which the adapter classifies as
`OllamaResponseError` and the service correctly falls back to the
deterministic formatter — this was observed directly, not just unit-tested,
and confirms the fallback path works against a real (if misconfigured)
Ollama instance, not only mocks. Run `ollama pull llama3.1:8b` to use the
real model end to end.

## 5. Ollama API Contract

`POST {OLLAMA_BASE_URL}/api/chat` with
`{"model": "llama3.1:8b", "messages": [...], "stream": false}`, implemented
in `app/ai/ollama_client.py::chat`. Verified by
`backend/tests/test_ai_ollama_client.py` against a monkeypatched
`httpx.AsyncClient` (model name, message array, `stream: false`, and the
exact URL are all asserted) — no live Ollama instance is needed for this or
any other automated test.

## 6. Inference Location

Strictly server-side: `React -> FastAPI -> app/ai/service.py -> Ollama`. The
frontend only ever calls `POST /api/v1/ai/ask` on the FastAPI backend
(`src/api/endpoints.ts::aiApi.ask`); `OLLAMA_BASE_URL` and the Ollama client
exist only in `backend/app/ai/`. No model credentials or server secrets are
exposed to the browser (Ollama needs none in the first place).

## 7. Intent Router

`app/ai/intent_router.py::classify_intent` is a pure, synchronous,
regex-based function with no LLM call and no database access — fully
independent of Ollama and fast by construction. It returns one of 10 typed
intents (`RANGE_DROP`, `ENERGY_EFFICIENCY`, `BATTERY_STRESS`, `ANOMALY`,
`COST`, `WHAT_IF`, `RECOMMENDATIONS`, `DRIVE_COMPARISON`, `GENERAL_VEHICLE`,
`UNKNOWN`), with rule order resolving the required ambiguous case ("what if
... why" routes to `WHAT_IF`, not `RANGE_DROP`). 14 dedicated tests in
`test_ai_intent_router.py`.

## 8. Intelligence Services

`app/ai/intelligence_bridge.py` exposes the ten typed services the spec
requires (`get_why_range_dropped`, `get_energy_analysis`,
`get_range_estimate`, `get_anomaly_analysis`, `get_battery_stress`,
`get_contributors`, `get_recommendations`, `get_vehicle_summary`,
`run_what_if`, `calculate_cost`). Every one of them delegates to the
existing Sprint 2 engines (`IntelligenceOrchestrator`, `WhatIfEngine`,
`CostAnalyzer`) — no formula is reimplemented. `run_what_if` passes
`base_simulation_id=None` through to `WhatIfEngine`, which already resolves
the latest suitable driving simulation itself; the AI layer never
hardcodes or invents a simulation ID.

## 9. Grounding

- Evidence and actions are closed Pydantic schemas
  (`model_config = ConfigDict(extra="forbid")`) with a fixed field set — there
  is no field for battery degradation, charger availability, or vehicle
  connectivity, so none of those can ever be expressed, let alone fabricated.
- Confidence is **never** parsed from the model. The LLM's only contribution
  to the response is the `"answer"` string; evidence, actions, confidence,
  intent, and data_sources are always backend-computed and simply attached.
  `test_confidence_is_never_upgraded_by_a_mocked_ollama_reply` proves this by
  feeding the mock an artificially "confident" answer and asserting the
  response's confidence still exactly matches the intelligence engine's own
  value for the same drive.
- The system prompt (`app/ai/system_prompt.py`) explicitly forbids inventing
  metrics, presenting simulation as live telemetry, upgrading confidence,
  claiming connectivity/charger availability, or claiming degradation not in
  evidence.

## 10. System Prompt

Backend-owned, defined once in `app/ai/system_prompt.py`, always injected as
the first message server-side; the frontend's `conversation` field can only
contain `user`/`assistant` roles (`role: Literal["user", "assistant"]`
rejects `"system"` with a 422) — verified in
`test_ai_conversation.py::test_system_role_cannot_be_supplied_by_frontend`
and the equivalent `AskRequest` test.

## 11. Response Schema

`AskResponse`: `intent`, `answer`, `evidence[]`, `actions[]`, `confidence`,
`data_sources[]`, `provider` (`"ollama" | "deterministic"`), `fallback_used`.
Mirrored exactly on the frontend in `src/api/types.ts`.

## 12. Conversation

Bounded to 6 exchanges / 12 messages on both sides: `app/ai/conversation.py`
(backend, authoritative) and `src/ai/conversation.ts` (frontend, keeps the
Ask screen's own history list and outgoing payload small). The 1st, 6th, and
7th-exchange boundary cases are explicitly tested on both sides. The current
question is always appended after the retained history; the system prompt is
never counted as an exchange.

## 13. Voice

`window.SpeechRecognition` / `webkitSpeechRecognition` only — no Whisper, no
cloud STT, no server audio upload. States: `IDLE`, `LISTENING`,
`PROCESSING`, `RESULT`, `ERROR`, `UNAVAILABLE`. Unsupported browsers see
"Voice input isn't available here. You can type your question instead."
mocked tests in `src/voice/useSpeechRecognition.test.ts` (9 tests) cover
every state transition, including permission-denied vs. generic errors and
retry.

## 14. Camera

`navigator.mediaDevices.getUserMedia` for "Scan Vehicle": permission,
preview, capture, retake, cancel, unsupported. Capturing a frame never
implies analysis — the UI states "Image analysis isn't available in this
prototype yet." with no OCR or fault-detection logic anywhere.
`src/camera/useCamera.test.ts` (8 tests) and
`src/components/ScanVehicle.test.tsx` (4 tests).

## 15. Sensors

Not implemented as a feature: the canonical demo flow and required UI tests
don't call for GPS/accelerometer/gyroscope, and the spec only constrains
phone-sensor labeling *if used* ("Phone sensor", never "Vehicle telemetry").
Since nothing in the app reads a phone sensor, there is nothing to mislabel.

## 16. Office Kit

Real, working implementations — never faked:
- **Copy Insight** (`WhyRange`) / **Copy Simulation Result** (`WhatIf`): the
  real Clipboard API via `src/office/clipboard.ts`, formatted by
  `src/office/insights.ts` into plain prose (verified to contain no `{`/`}`).
- **Export Drive Report** (`Vehicle`): a real Markdown file via
  `src/office/exportReport.ts` + `src/office/download.ts` (Blob + anchor
  click), with all eight required sections and the simulation disclaimer.
- **Share**: `src/office/share.ts` uses the real Web Share API when present,
  falling back to the clipboard, reporting `cancelled`/`copied`/`unavailable`
  honestly.

## 17. Export

See section 16. `src/office/exportReport.test.ts` (6 tests) and
`src/office/insights.test.ts` (8 tests) verify every required section header,
the disclaimer text, real (non-placeholder) vehicle/simulation IDs, the
absence of secret-shaped strings, and human-readable (non-JSON) clipboard
text.

## 18. Security

No secrets introduced: Ollama needs no API key. `.env.example` documents only
non-secret configuration. No stack traces, hidden prompts, or test data are
ever returned to the client — `IntelligenceUnavailableError` and
`WhatIfFailedError` carry only the fixed, driver-friendly message strings
from `app/ai/service.py`, and `test_ai_endpoint.py` asserts the literal word
"Traceback" never appears in a 404 response body.

## 19. Error Handling

| Failure | Handling |
|---|---|
| Ollama unavailable / timeout / malformed output | Deterministic fallback, `provider: "deterministic"`, `fallback_used: true` |
| No suitable simulation | HTTP 404, "No suitable driving simulation is available for this vehicle." |
| What-if execution failure | HTTP 500, driver-friendly message |
| Missing electricity price | No error — `COST` intent returns a `VIEW_COST` action instead of calling the calculator |
| Microphone denied/unsupported | Voice `ERROR`/`UNAVAILABLE` state with a plain-language message |
| Camera denied/unsupported | Camera `DENIED`/`UNSUPPORTED` state with a plain-language message |
| Export/share failure | `shareText` reports `unavailable`; export only enables once data has loaded |

## 20. Testing

**Backend (pytest), new files:**
`test_ai_intent_router.py` (14), `test_ai_conversation.py` (10),
`test_ai_ollama_client.py` (8), `test_ai_grounding.py` (16),
`test_ai_endpoint.py` (24) — **72 new tests**, all mocking Ollama; none
requires a live model.

**Frontend (Vitest), new/extended files:**
`ai/conversation.test.ts` (8), `ai/actions.test.ts` (1),
`voice/useSpeechRecognition.test.ts` (9), `camera/useCamera.test.ts` (8),
`office/clipboard.test.ts` (3), `office/share.test.ts` (4),
`office/download.test.ts` (2), `office/insights.test.ts` (8),
`office/exportReport.test.ts` (6), `components/AnswerCard.test.tsx` (8),
`components/ScanVehicle.test.tsx` (4), plus Sprint 4 additions to
`Ask.test.tsx`, `Home.test.tsx`, `Drive.test.tsx`, `Vehicle.test.tsx`,
`WhyRange.test.tsx`, `WhatIf.test.tsx` — **73 new tests**.

## 21. Regression

- Backend: **169 passed** (97 original + 72 new), 0 failed.
- Frontend: **192 passed** (119 original + 73 new), 0 failed.
- No Sprint 1–3 test was modified, weakened, or deleted.

## 22. Build

`npm run build` (`tsc --noEmit && vite build`): **success**.
`dist/assets/index-*.js` 318.76 kB (gzip 99.08 kB),
`dist/assets/index-*.css` 12.46 kB (gzip 3.46 kB). No warnings.

## 23. Browser QA

Not performed as live interactive Chrome QA in this session (no browser
automation was available in this environment) — see Known Limitations. All
UI behavior is instead covered by the 73 new Vitest/Testing-Library tests,
which exercise real DOM rendering, focus, ARIA roles, and user-event
interactions under jsdom, but this is not a substitute for manual visual QA
on the four target viewports.

## 24. Known Limitations

- `llama3.1:8b` is not pulled on this machine (only `qwen2.5vl:3b` is); live
  AI answers will use the deterministic fallback until it's pulled.
- No live, interactive Chrome QA across the four target viewports (390×844,
  375×812, 412×915, 1440×900) was performed in this session.
- `ask/intents.ts`'s `routeAsk`/`UNKNOWN_INTENT_COPY` are no longer called
  from `Ask.tsx` (superseded by the real AI endpoint) but were left in place,
  still correct and still tested, rather than deleted, to avoid removing
  existing Sprint 3 tests; `SUGGESTED_PROMPTS` from the same module is still
  used.
- Phone sensors (GPS/accelerometer) are not implemented — see section 15.
- jsdom has no real `<canvas>` 2D context, so `useCamera`'s captured-image
  data URL is an empty string under test; this is a test-environment
  limitation, not an application bug (verified against a real `<video>`
  element path).

## 25. Final Verdict

See below.
