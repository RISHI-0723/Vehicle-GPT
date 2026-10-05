// Deterministic keyword intent routing for the Ask screen. No LLM and no fuzzy guessing:
// anything not matched returns null and the UI shows the explicit capability fallback.

export type AskIntent = "why-range" | "what-if" | "battery-stress" | "anomaly" | "energy" | "cost";

export interface AskRoute {
  intent: AskIntent;
  path: string;
  label: string;
}

const ROUTES: Record<AskIntent, AskRoute> = {
  "why-range": { intent: "why-range", path: "/why-range", label: "Why did my range drop?" },
  "what-if": { intent: "what-if", path: "/what-if", label: "What if I drove normally?" },
  "battery-stress": { intent: "battery-stress", path: "/vehicle#battery-stress", label: "Check battery stress" },
  anomaly: { intent: "anomaly", path: "/vehicle#anomaly", label: "Was my last drive abnormal?" },
  energy: { intent: "energy", path: "/drive", label: "How much energy did I use?" },
  cost: { intent: "cost", path: "/cost", label: "Calculate trip cost" },
};

// Order matters: more specific phrases are checked before broader ones.
const RULES: Array<{ intent: AskIntent; pattern: RegExp }> = [
  { intent: "what-if", pattern: /\bwhat\s+if\b|\bnormally\b/ },
  { intent: "why-range", pattern: /\bwhy\b|range\s+(dropped|drop|lower|low|changed|change)/ },
  { intent: "cost", pattern: /\bcost\b|\bspend|\bspent\b|\bprice\b|\bmoney\b|\bpay\b|₹/ },
  { intent: "battery-stress", pattern: /\bstress/ },
  { intent: "anomaly", pattern: /anomal|abnormal|unusual/ },
  { intent: "energy", pattern: /\benergy\b|\bkwh\b|\bconsum/ },
];

export function routeAsk(input: string): AskRoute | null {
  const text = input.trim().toLowerCase();
  if (text.length === 0) return null;
  for (const rule of RULES) {
    if (rule.pattern.test(text)) return ROUTES[rule.intent];
  }
  return null;
}

export const SUGGESTED_PROMPTS: AskRoute[] = [
  ROUTES["why-range"],
  ROUTES["what-if"],
  ROUTES["energy"],
  ROUTES["battery-stress"],
  ROUTES.anomaly,
  ROUTES.cost,
];

export const UNKNOWN_INTENT_COPY =
  "I can help with your vehicle's range, energy use, battery stress, driving behavior, and cost.";
