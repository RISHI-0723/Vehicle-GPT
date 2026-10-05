// Test fixtures shaped exactly like the backend responses (values mirror a real probe run).
import type {
  AnomalyDetection,
  AskResponse,
  BatteryStress,
  ContributorAnalysis,
  CostResponse,
  EnergyAnalysis,
  RangeEstimation,
  Recommendation,
  Recommendations,
  VehicleInfo,
  WhatIfResponse,
  WhyRangeDropped,
} from "../api/types";
import type { CanonicalDemo } from "../demo/canonical";
import type { DriveRecord } from "../demo/discovery";

export const HERO_ID = "sim-aggressive01";
export const NORMAL_ID = "sim-normal0001";
export const VEHICLE_ID = "VG-DEMO-001";

export function energyFixture(overrides: Partial<EnergyAnalysis> = {}): EnergyAnalysis {
  return {
    energy_consumed_kwh: 11.4634,
    energy_regenerated_kwh: 0.5,
    net_energy_kwh: 10.9634,
    distance_km: 56.2,
    energy_per_km: 0.204,
    regen_ratio: 0.04,
    efficiency_delta_percent: 107.7,
    rating: "INEFFICIENT",
    rating_reason: "Consumption is above the reference band.",
    duration_seconds: 1800,
    sample_count: 180,
    baseline_simulation_id: NORMAL_ID,
    baseline_match_type: "EXACT",
    ...overrides,
  };
}

export function rangeFixture(overrides: Partial<RangeEstimation> = {}): RangeEstimation {
  return {
    current_soc_percent: 81.16,
    remaining_energy_kwh: 46.26,
    efficiency_kwh_per_km: 0.204,
    efficiency_source: "recent telemetry",
    estimated_range_km: 226.73,
    confidence: "HIGH",
    confidence_reason: "Enough distance and samples.",
    disclaimer: "Estimate from synthetic telemetry.",
    ...overrides,
  };
}

export function contributorsFixture(overrides: Partial<ContributorAnalysis> = {}): ContributorAnalysis {
  return {
    contributors: [
      {
        id: "aggressive_driving",
        name: "Aggressive driving",
        observed_value: 47.9,
        baseline_value: 8.3,
        difference: 39.6,
        difference_percent: 477,
        impact_score: 88,
        impact_level: "CRITICAL",
        description: "Driving score is well above the normal drive.",
        is_available: true,
      },
      {
        id: "max_speed",
        name: "Maximum speed",
        observed_value: 98,
        baseline_value: 70,
        difference: 28,
        difference_percent: 40,
        impact_score: 55,
        impact_level: "HIGH",
        description: "Peak speed was higher than the normal drive.",
        is_available: true,
      },
      {
        id: "ambient_temperature",
        name: "Ambient temperature",
        observed_value: 26,
        baseline_value: null,
        difference: null,
        difference_percent: null,
        impact_score: 0,
        impact_level: "UNAVAILABLE",
        description: "No comparison available.",
        is_available: false,
      },
    ],
    total_contributors: 3,
    available_contributors: 2,
    baseline_available: true,
    baseline_simulation_id: NORMAL_ID,
    baseline_match_type: "EXACT",
    summary: "Driving style contributed most.",
    ...overrides,
  };
}

export function anomalyFixture(overrides: Partial<AnomalyDetection> = {}): AnomalyDetection {
  return {
    anomaly_score: 81.17,
    severity: "HIGH",
    is_anomalous: true,
    reasons: ["Energy use is well above the baseline."],
    components: [],
    baseline_available: true,
    baseline_simulation_id: NORMAL_ID,
    baseline_match_type: "EXACT",
    confidence: "High",
    ...overrides,
  };
}

export function stressFixture(overrides: Partial<BatteryStress> = {}): BatteryStress {
  return {
    battery_stress_score: 61,
    stress_level: "ELEVATED",
    components: [],
    explanation: "Operating stress is elevated during this drive.",
    c_rate_average: 0.1,
    c_rate_max: 0.7,
    high_temperature_exposure_percent: 12,
    disclaimer: "Operational stress only. Not a health prediction.",
    ...overrides,
  };
}

export function recommendationFixtures(count = 3): Recommendation[] {
  const base: Recommendation[] = [
    {
      id: "CHECK_ENERGY_ANOMALY",
      title: "Check energy use",
      priority: "URGENT",
      reason: "Energy use is well above the baseline.",
      expected_benefit: "Helps confirm whether the drive was unusual.",
      related_metric: "energy_deviation",
      impact_score: 90,
    },
    {
      id: "REDUCE_SPEED",
      title: "Drive slightly slower",
      priority: "HIGH",
      reason: "Higher speeds increased consumption.",
      expected_benefit: "Improves range.",
      related_metric: "speed",
      impact_score: 60,
    },
    {
      id: "SMOOTHER_ACCELERATION",
      title: "Smoother acceleration",
      priority: "MEDIUM",
      reason: "Harsh acceleration events were frequent.",
      expected_benefit: "Reduces energy spikes.",
      related_metric: "acceleration",
      impact_score: 40,
    },
    {
      id: "USE_REGEN_EFFECTIVELY",
      title: "Use regeneration",
      priority: "LOW",
      reason: "Regeneration was low.",
      expected_benefit: "Recovers more energy.",
      related_metric: "regen",
      impact_score: 20,
    },
    {
      id: "AVOID_DEEP_SOC_SWINGS",
      title: "Avoid deep charge swings",
      priority: "LOW",
      reason: "SOC moved a lot.",
      expected_benefit: "Lowers operating stress.",
      related_metric: "soc",
      impact_score: 10,
    },
    {
      id: "REDUCE_FAST_CHARGING_STRESS",
      title: "Reduce fast-charging stress",
      priority: "LOW",
      reason: "Fast charging was used.",
      expected_benefit: "Lowers operating stress.",
      related_metric: "c_rate",
      impact_score: 5,
    },
  ];
  return base.slice(0, count);
}

export function recommendationsFixture(count = 3): Recommendations {
  const items = recommendationFixtures(count);
  return { recommendations: items, total_generated: items.length, total_returned: items.length };
}

export function whyFixture(overrides: Partial<WhyRangeDropped> = {}): WhyRangeDropped {
  return {
    vehicle_id: VEHICLE_ID,
    observed_simulation_id: HERO_ID,
    observed_scenario: "AGGRESSIVE_DRIVING",
    baseline_simulation_id: NORMAL_ID,
    baseline_match_type: "EXACT",
    energy: energyFixture(),
    range_estimate: rangeFixture(),
    contributors: contributorsFixture(),
    anomaly: anomalyFixture(),
    battery_stress: stressFixture(),
    recommendations: recommendationsFixture(3),
    explanation: {
      headline: "Significant efficiency drop reduced your estimated range",
      summary: "Your energy consumption was higher than your normal baseline.",
      key_factors: ["Aggressive driving score was 47.9 vs baseline 8.3"],
      recommendation_summary: "Top recommendations: Check energy use.",
      confidence: "High",
    },
    confidence: "HIGH",
    ...overrides,
  };
}

export function summaryFixture(overrides: Partial<WhyRangeDropped> = {}): WhyRangeDropped {
  return whyFixture(overrides);
}

export function whatIfFixture(overrides: Partial<WhatIfResponse> = {}): WhatIfResponse {
  return {
    base_simulation_id: HERO_ID,
    base_scenario: "AGGRESSIVE_DRIVING",
    counterfactual_scenario: "NORMAL_DRIVING",
    starting_soc_percent: 80,
    base_metrics: {
      scenario: "AGGRESSIVE_DRIVING",
      starting_soc_percent: 80,
      ending_soc_percent: 81.16,
      energy_consumed_kwh: 11.46,
      distance_km: 56.2,
      estimated_range_km: 226.73,
      duration_seconds: 1800,
      sample_count: 180,
    },
    counterfactual_metrics: {
      scenario: "NORMAL_DRIVING",
      starting_soc_percent: 80,
      ending_soc_percent: 75.22,
      energy_consumed_kwh: 3.28,
      distance_km: 54.1,
      estimated_range_km: 436.35,
      duration_seconds: 1800,
      sample_count: 180,
    },
    energy_change_kwh: -8.18,
    energy_change_percent: -71.4,
    estimated_range_change_km: 209.62,
    interpretation: "If you had driven with NORMAL_DRIVING instead of AGGRESSIVE_DRIVING, the counterfactual shows 71.4% less energy consumed with approximately 209.6 km more estimated range.",
    ...overrides,
  };
}

export function fastChargingWhatIfFixture(): WhatIfResponse {
  return whatIfFixture({
    counterfactual_scenario: "FAST_CHARGING",
    counterfactual_metrics: {
      scenario: "FAST_CHARGING",
      starting_soc_percent: 80,
      ending_soc_percent: 95.1,
      energy_consumed_kwh: 14.2,
      distance_km: 0,
      estimated_range_km: null,
      duration_seconds: 1800,
      sample_count: 180,
    },
    energy_change_kwh: 2.74,
    energy_change_percent: 23.9,
    estimated_range_change_km: null,
    interpretation: "Counterfactual charging scenario simulated. Range comparison not applicable for charging sessions.",
  });
}

export function costFixture(overrides: Partial<CostResponse> = {}): CostResponse {
  return {
    energy_cost_inr: 87.71,
    electricity_price_per_kwh: 8,
    energy_used_kwh: 10.96,
    wear_factor: 0.2456,
    estimated_battery_wear_cost_inr: 0.36,
    total_operating_cost_inr: 88.07,
    cost_per_km_inr: 1.57,
    distance_km: 56.2,
    duration_seconds: 1800,
    disclaimer: "Battery wear cost is a prototype proxy, not a degradation model.",
    ...overrides,
  };
}

export function vehicleFixture(): VehicleInfo {
  return {
    vehicle_id: VEHICLE_ID,
    make: "VehicleGPT",
    model: "EV Demo",
    model_year: 2026,
    battery_capacity_kwh: 60,
    usable_battery_capacity_kwh: 57,
    battery_type: "LFP",
  };
}

export function driveRecordFixture(overrides: Partial<DriveRecord> = {}): DriveRecord {
  return {
    simulationId: HERO_ID,
    scenario: "AGGRESSIVE_DRIVING",
    sampleCount: 180,
    startTime: "2026-01-01T00:00:00Z",
    endTime: "2026-01-01T00:30:00Z",
    stepSeconds: 10,
    durationMinutes: 30,
    endSocPercent: 78.4,
    endBatteryTemperatureC: 31.2,
    ...overrides,
  };
}

/** A ready CanonicalDemo as the app sees it once both hero drives are resolved. */
export function heroFixture(): CanonicalDemo {
  return {
    normal: driveRecordFixture({ simulationId: NORMAL_ID, scenario: "NORMAL_DRIVING" }),
    aggressive: driveRecordFixture({ simulationId: HERO_ID, scenario: "AGGRESSIVE_DRIVING" }),
  };
}

export function askResponseFixture(overrides: Partial<AskResponse> = {}): AskResponse {
  return {
    intent: "RANGE_DROP",
    answer: "Your range dropped mainly because of aggressive driving compared to your normal baseline.",
    evidence: [
      { id: "estimated_range", label: "Estimated range", value: 226.73, unit: "km" },
      {
        id: "energy_consumption",
        label: "Energy consumption",
        value: 20.4,
        unit: "kWh/100km",
        comparison: "14.9 kWh/100km baseline",
        direction: "higher",
        impact_level: "INEFFICIENT",
      },
    ],
    actions: [
      { id: "WHAT_IF_NORMAL", label: "What if I drove normally?", type: "WHAT_IF" },
      { id: "VIEW_CONTRIBUTORS", label: "See main contributors", type: "VIEW_CONTRIBUTORS" },
    ],
    confidence: "HIGH",
    data_sources: ["why-range-dropped"],
    provider: "ollama",
    fallback_used: false,
    ...overrides,
  };
}

export function askCostNeedsPriceFixture(): AskResponse {
  return askResponseFixture({
    intent: "COST",
    answer: "To calculate the drive cost, enter your electricity price.",
    evidence: [],
    actions: [{ id: "OPEN_COST", label: "Calculate drive cost", type: "VIEW_COST" }],
    confidence: "HIGH",
    data_sources: [],
    provider: "deterministic",
    fallback_used: false,
  });
}

export function askCostWithPriceFixture(): AskResponse {
  return askResponseFixture({
    intent: "COST",
    answer: "This drive cost an estimated 88.07 INR.",
    evidence: [{ id: "total_operating_cost", label: "Total operating cost", value: 88.07, unit: "INR" }],
    actions: [],
    confidence: "HIGH",
    data_sources: ["cost"],
  });
}

export function askWhatIfFixture(): AskResponse {
  return askResponseFixture({
    intent: "WHAT_IF",
    answer: "If you had driven normally, the counterfactual shows 71.4% less energy consumed.",
    evidence: [
      { id: "range_change", label: "Estimated range difference", value: 209.62, unit: "km", direction: "higher" },
    ],
    actions: [],
    data_sources: ["what-if"],
  });
}

export function askUnknownFixture(): AskResponse {
  return askResponseFixture({
    intent: "UNKNOWN",
    answer: "I can help with range, efficiency, battery stress, drive comparisons, cost, and what-if scenarios.",
    evidence: [],
    actions: [],
    confidence: "LOW",
    data_sources: [],
    provider: "deterministic",
    fallback_used: true,
  });
}
