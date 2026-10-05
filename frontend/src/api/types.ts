// Types mirror the FastAPI/Pydantic schemas in backend/app/schemas.
// The backend is the source of truth; these are contracts, not calculations.

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type BaselineMatchType = "EXACT" | "APPROXIMATE" | "UNAVAILABLE";
export type EfficiencyRating = "EFFICIENT" | "NORMAL" | "INEFFICIENT" | "UNKNOWN";
export type ImpactLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "UNAVAILABLE";
export type AnomalySeverity = "NORMAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type StressLevel = "LOW" | "MODERATE" | "ELEVATED" | "HIGH" | "CRITICAL";
export type RecommendationPriority = "URGENT" | "HIGH" | "MEDIUM" | "LOW";

export interface EnergyAnalysis {
  energy_consumed_kwh: number;
  energy_regenerated_kwh: number;
  net_energy_kwh: number;
  distance_km: number;
  energy_per_km: number | null;
  regen_ratio: number | null;
  efficiency_delta_percent: number | null;
  rating: EfficiencyRating;
  rating_reason: string;
  duration_seconds: number;
  sample_count: number;
  baseline_simulation_id: string | null;
  baseline_match_type: BaselineMatchType;
}

export interface RangeEstimation {
  current_soc_percent: number;
  remaining_energy_kwh: number;
  efficiency_kwh_per_km: number | null;
  efficiency_source: string;
  estimated_range_km: number | null;
  confidence: ConfidenceLevel;
  confidence_reason: string;
  disclaimer: string;
}

export interface Contributor {
  id: string;
  name: string;
  observed_value: number | null;
  baseline_value: number | null;
  difference: number | null;
  difference_percent: number | null;
  impact_score: number;
  impact_level: ImpactLevel;
  description: string;
  is_available: boolean;
}

export interface ContributorAnalysis {
  contributors: Contributor[];
  total_contributors: number;
  available_contributors: number;
  baseline_available: boolean;
  baseline_simulation_id: string | null;
  baseline_match_type: BaselineMatchType;
  summary: string;
}

export interface AnomalyComponent {
  name: string;
  observed_value: number | null;
  baseline_value: number | null;
  deviation_ratio: number;
  weighted_contribution: number;
  weight: number;
  description: string;
}

export interface AnomalyDetection {
  anomaly_score: number;
  severity: AnomalySeverity;
  is_anomalous: boolean;
  reasons: string[];
  components: AnomalyComponent[];
  baseline_available: boolean;
  baseline_simulation_id: string | null;
  baseline_match_type: BaselineMatchType;
  confidence: string;
}

export interface StressComponent {
  name: string;
  raw_score: number;
  weight: number;
  weighted_score: number;
  description: string;
}

export interface BatteryStress {
  battery_stress_score: number;
  stress_level: StressLevel;
  components: StressComponent[];
  explanation: string;
  c_rate_average: number;
  c_rate_max: number;
  high_temperature_exposure_percent: number;
  disclaimer: string;
}

export interface Recommendation {
  id: string;
  title: string;
  priority: RecommendationPriority;
  reason: string;
  expected_benefit: string;
  related_metric: string;
  impact_score: number;
}

export interface Recommendations {
  recommendations: Recommendation[];
  total_generated: number;
  total_returned: number;
}

export interface Explanation {
  headline: string;
  summary: string;
  key_factors: string[];
  recommendation_summary: string;
  confidence: string;
}

export interface WhyRangeDropped {
  vehicle_id: string;
  observed_simulation_id: string;
  observed_scenario: string;
  baseline_simulation_id: string | null;
  baseline_match_type: BaselineMatchType;
  energy: EnergyAnalysis;
  range_estimate: RangeEstimation;
  contributors: ContributorAnalysis;
  anomaly: AnomalyDetection;
  battery_stress: BatteryStress;
  recommendations: Recommendations;
  explanation: Explanation;
  confidence: ConfidenceLevel;
}

export type IntelligenceSummary = WhyRangeDropped;

export interface WhatIfRequest {
  vehicle_id: string;
  counterfactual_scenario: string;
  base_simulation_id?: string;
  duration_minutes?: number;
  interval_seconds?: number;
  seed?: number;
}

export interface WhatIfMetrics {
  scenario: string;
  starting_soc_percent: number;
  ending_soc_percent: number;
  energy_consumed_kwh: number;
  distance_km: number;
  estimated_range_km: number | null;
  duration_seconds: number;
  sample_count: number;
}

export interface WhatIfResponse {
  base_simulation_id: string;
  base_scenario: string;
  counterfactual_scenario: string;
  starting_soc_percent: number;
  base_metrics: WhatIfMetrics;
  counterfactual_metrics: WhatIfMetrics;
  energy_change_kwh: number | null;
  energy_change_percent: number | null;
  estimated_range_change_km: number | null;
  interpretation: string;
}

export interface CostRequest {
  vehicle_id: string;
  simulation_id?: string;
  electricity_price_per_kwh: number;
  battery_replacement_cost_per_kwh_inr?: number;
  wear_cost_fraction?: number;
}

export interface CostResponse {
  energy_cost_inr: number;
  electricity_price_per_kwh: number;
  energy_used_kwh: number;
  wear_factor: number;
  estimated_battery_wear_cost_inr: number;
  total_operating_cost_inr: number;
  cost_per_km_inr: number | null;
  distance_km: number;
  duration_seconds: number;
  disclaimer: string;
}

export interface VehicleInfo {
  vehicle_id: string;
  make: string;
  model: string;
  model_year: number;
  battery_capacity_kwh: number;
  usable_battery_capacity_kwh: number;
  battery_type: string;
}

export interface TelemetryItem {
  telemetry_id: number;
  simulation_id: string;
  vehicle_id: string;
  timestamp: string;
  soc_percent: number;
  battery_temperature_c: number;
  speed_kmh: number;
  battery_power_kw: number;
  charging: boolean;
}

export interface TelemetryPage {
  vehicle_id: string;
  count: number;
  limit: number;
  offset: number;
  items: TelemetryItem[];
}

export interface SimulationRunRequest {
  vehicle_id: string;
  scenario: string;
  duration_minutes: number;
  interval_seconds: number;
  seed: number;
  mode: "fresh" | "continue";
  simulation_start_time?: string;
}

export interface SimulationRunResponse {
  simulation_id: string;
  vehicle_id: string;
  scenario: string;
  mode: string;
  seed: number;
  start_time: string;
  duration_minutes: number;
  interval_seconds: number;
  samples_generated: number;
  starting_soc: number;
  ending_soc: number;
  energy_consumed: number;
  distance: number;
}

export interface ResetResponse {
  vehicle_id: string;
  telemetry_deleted: number;
  simulations_deleted: number;
  message: string;
}

// === Sprint 4: AI ask endpoint ===
// Mirrors backend/app/ai/schemas.py exactly. Confidence, evidence and actions
// always come from this contract -- the frontend never invents any of them.

export type AiIntent =
  | "RANGE_DROP"
  | "ENERGY_EFFICIENCY"
  | "BATTERY_STRESS"
  | "ANOMALY"
  | "COST"
  | "WHAT_IF"
  | "RECOMMENDATIONS"
  | "DRIVE_COMPARISON"
  | "GENERAL_VEHICLE"
  | "UNKNOWN";

export type ActionType =
  | "WHAT_IF"
  | "VIEW_DRIVE"
  | "VIEW_CONTRIBUTORS"
  | "VIEW_RECOMMENDATIONS"
  | "VIEW_COST"
  | "VIEW_BATTERY";

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface EvidenceItem {
  id: string;
  label: string;
  value?: number | null;
  unit?: string | null;
  comparison?: string | null;
  direction?: "higher" | "lower" | "same" | null;
  impact_level?: string | null;
}

export interface ActionItem {
  id: string;
  label: string;
  type: ActionType;
}

export interface AskRequest {
  vehicle_id: string;
  question: string;
  conversation?: ConversationMessage[];
  electricity_price_per_kwh?: number;
}

export interface AskResponse {
  intent: AiIntent;
  answer: string;
  evidence: EvidenceItem[];
  actions: ActionItem[];
  confidence: ConfidenceLevel;
  data_sources: string[];
  provider: "ollama" | "deterministic";
  fallback_used: boolean;
}
