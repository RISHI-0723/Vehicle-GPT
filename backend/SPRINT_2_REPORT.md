# VehicleGPT Sprint 2 Report

**Project:** VehicleGPT - EV Intelligence Engine
**Sprint:** 2 - Deterministic Intelligence Engine
**Hackathon:** iQOO Hackathon 2026 Mobility Grand Finale
**Date:** October 2026

---

## 1. Objective

Build a **deterministic EV intelligence layer** on top of the Sprint 1 simulator. The intelligence engine provides analytics, diagnostics, and recommendations based on simulated telemetry data. All analysis is computed locally using rule-based algorithms with no external APIs, no LLMs, and no machine learning models.

**Key Constraints:**
- No Sprint 3 features (voice assistant, mobile UI, production deployment)
- All telemetry is synthetic simulated data
- All computations are deterministic and reproducible
- All intelligence endpoints are side-effect free (no database mutations)
- Sprint 1 backward compatibility maintained

---

## 2. Architecture

### Module Structure

```
backend/app/intelligence/
├── __init__.py           # Module exports
├── config.py             # Locked thresholds, weights, and parameters
├── features.py           # Shared feature extraction pipeline
├── baseline.py           # Baseline selection service
├── energy.py             # Energy analysis service
├── range_estimator.py    # Range estimation service
├── contributors.py       # Contributor analysis service
├── anomaly.py            # Anomaly detection service
├── battery_stress.py     # Battery stress analysis service
├── what_if.py            # What-if counterfactual engine
├── cost.py               # Cost-of-driving analysis engine
├── recommendations.py    # Recommendation engine
├── explanation.py        # Template-based explanation builder
└── orchestrator.py       # Composite why-range orchestrator
```

### Data Flow

```
Telemetry Records (from Sprint 1)
         │
         ▼
┌─────────────────────┐
│ Feature Extraction  │ ──► Shared FeatureVector
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Baseline Selection  │ ──► BaselineResult (EXACT/APPROXIMATE/UNAVAILABLE)
└─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                  Analysis Services                       │
│  Energy │ Range │ Contributors │ Anomaly │ Battery      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Recommendation Eng. │ ──► Max 5 deduplicated recommendations
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Explanation Builder │ ──► Natural language explanations
└─────────────────────┘
```

---

## 3. Intelligence Modules

### 3.1 Configuration (`config.py`)

Centralized configuration with locked values:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `BASELINE_SCENARIO` | `NORMAL_DRIVING` | Canonical baseline scenario |
| `NOMINAL_EFFICIENCY` | 6.5 km/kWh | Demo EV reference efficiency |
| `ENERGY_WEIGHT` | 0.60 | Anomaly detection weight |
| `SPEED_WEIGHT` | 0.20 | Anomaly detection weight |
| `ACCEL_WEIGHT` | 0.10 | Anomaly detection weight |
| `TEMP_WEIGHT` | 0.10 | Anomaly detection weight |
| `ANOMALY_THRESHOLD` | 0.15 | Score threshold for anomaly flag |
| `MAX_RECOMMENDATIONS` | 5 | Maximum recommendations returned |

### 3.2 Feature Extraction (`features.py`)

Extracts a `FeatureVector` from telemetry records:

- `total_energy_kwh`: Sum of energy consumed
- `total_regen_kwh`: Sum of regenerative energy
- `net_energy_kwh`: Total - Regen
- `total_distance_km`: Sum of distance traveled
- `efficiency_km_per_kwh`: Distance / Net Energy
- `avg_speed_kmh`: Mean speed
- `max_speed_kmh`: Maximum speed
- `avg_acceleration`: Mean acceleration
- `max_acceleration`: Maximum acceleration
- `avg_battery_temp_c`: Mean battery temperature
- `max_battery_temp_c`: Maximum battery temperature
- `min_soc_percent`: Minimum state of charge
- `max_soc_percent`: Maximum state of charge
- `soc_delta`: Max SOC - Min SOC
- `avg_power_kw`: Mean battery power
- `max_power_kw`: Maximum battery power
- `record_count`: Number of telemetry records
- `duration_minutes`: Total duration

### 3.3 Baseline Selection (`baseline.py`)

Match types:
- **EXACT**: Same scenario found in history
- **APPROXIMATE**: Different scenario with similar conditions (±10% efficiency)
- **UNAVAILABLE**: No suitable baseline found

Selection priority:
1. Exact scenario match (most recent)
2. Approximate match by efficiency similarity
3. Unavailable with fallback to nominal values

---

## 4. Energy Analysis

**Endpoint:** `GET /api/v1/intelligence/energy/{vehicle_id}`

- **Path parameters:** `vehicle_id` (string) - vehicle to analyze (demo vehicle: `VG-DEMO-001`)
- **Query parameters:** `simulation_id` (string, optional) - specific simulation; if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `EnergyAnalysisResponse`
  - `energy_consumed_kwh`, `energy_regenerated_kwh`, `net_energy_kwh`, `distance_km`
  - `energy_per_km`, `regen_ratio`, `efficiency_delta_percent` (nullable)
  - `rating`, `rating_reason`, `duration_seconds`, `sample_count`
  - `baseline_simulation_id` (nullable), `baseline_match_type`
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation or telemetry exists

Computes:
- Current session efficiency vs baseline efficiency
- Efficiency rating (EXCELLENT/GOOD/AVERAGE/POOR/CRITICAL)
- Deviation from nominal (6.5 km/kWh)
- Energy breakdown (consumption, regeneration, net)

**Rating Thresholds:**
| Rating | Efficiency Range |
|--------|------------------|
| EXCELLENT | ≥ 7.0 km/kWh |
| GOOD | 6.0 - 7.0 km/kWh |
| AVERAGE | 5.0 - 6.0 km/kWh |
| POOR | 4.0 - 5.0 km/kWh |
| CRITICAL | < 4.0 km/kWh |

---

## 5. Range Estimation

**Endpoint:** `GET /api/v1/intelligence/range/{vehicle_id}`

- **Path parameters:** `vehicle_id` (string)
- **Query parameters:** `simulation_id` (string, optional) - simulation used for recent efficiency; if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `RangeEstimationResponse`
  - `current_soc_percent`, `remaining_energy_kwh`, `efficiency_kwh_per_km` (nullable), `efficiency_source`
  - `estimated_range_km` (nullable; null when no valid driving efficiency exists, e.g. charging-only sessions)
  - `confidence`, `confidence_reason`, `disclaimer`
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation or telemetry exists

Computes estimated remaining range using:
- Current SOC and usable battery capacity (57 kWh)
- Recent efficiency (from telemetry)
- Baseline efficiency (for comparison)

**Confidence Levels** (based on distance and sample count):
| Level | Condition |
|-------|-----------|
| HIGH | ≥ 5.0 km distance and ≥ 10 telemetry samples |
| MEDIUM | ≥ 3 telemetry samples (below HIGH) |
| LOW | Otherwise |

Formula:
```
remaining_usable_energy_kwh = usable_battery_capacity_kwh × (current_soc / 100)
estimated_range_km = remaining_usable_energy_kwh / efficiency_kwh_per_km
```

---

## 6. Contributor Analysis

**Endpoint:** `GET /api/v1/intelligence/contributors/{vehicle_id}`

- **Path parameters:** `vehicle_id` (string)
- **Query parameters:** `simulation_id` (string, optional) - if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `ContributorAnalysisResponse`
  - `contributors`: list of `ContributorResponse` (`id`, `name`, `observed_value`, `baseline_value`, `difference`, `difference_percent`, `impact_score`, `impact_level`, `description`, `is_available`)
  - `total_contributors`, `available_contributors`, `baseline_available`
  - `baseline_simulation_id` (nullable), `baseline_match_type`, `summary`
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation or telemetry exists

Identifies factors contributing to efficiency differences:

| Contributor | Trigger Condition | Impact Level |
|-------------|-------------------|--------------|
| High Speed | Avg speed >100 km/h | HIGH |
| Aggressive Acceleration | Avg accel >2.0 m/s² | HIGH |
| Extreme Temperature | Temp >40°C or <5°C | HIGH |
| High Power Draw | Avg power >50 kW | MEDIUM |
| Low Regeneration | Regen <5% of consumption | MEDIUM |
| Moderate Speed | Avg speed >80 km/h | LOW |

Each contributor includes:
- Category and description
- Impact level (LOW/MEDIUM/HIGH/CRITICAL)
- Efficiency impact percentage
- Actionable suggestion

---

## 7. Anomaly Detection

**Endpoint:** `GET /api/v1/intelligence/anomaly/{vehicle_id}`

- **Path parameters:** `vehicle_id` (string)
- **Query parameters:** `simulation_id` (string, optional) - if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `AnomalyDetectionResponse`
  - `anomaly_score`, `severity`, `is_anomalous`, `reasons`, `confidence`
  - `components`: list of `AnomalyComponentResponse` (`name`, `observed_value`, `baseline_value`, `deviation_ratio`, `weighted_contribution`, `weight`, `description`)
  - `baseline_available`, `baseline_simulation_id` (nullable), `baseline_match_type`
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation or telemetry exists

**Locked Formula:**
```
anomaly_score = 0.60 × energy_deviation
             + 0.20 × speed_deviation
             + 0.10 × acceleration_deviation
             + 0.10 × temperature_deviation
```

**Severity Thresholds:**
| Severity | Score Range |
|----------|-------------|
| NONE | < 0.15 |
| LOW | 0.15 - 0.30 |
| MEDIUM | 0.30 - 0.50 |
| HIGH | ≥ 0.50 |

Output includes:
- Overall anomaly score
- Component scores for each factor
- Detected anomalies with descriptions
- Severity classification

---

## 8. Battery Stress Analysis

**Endpoint:** `GET /api/v1/intelligence/battery-stress/{vehicle_id}`

- **Path parameters:** `vehicle_id` (string)
- **Query parameters:** `simulation_id` (string, optional) - if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `BatteryStressResponse`
  - `battery_stress_score`, `stress_level`, `explanation`, `disclaimer`
  - `components`: list of `StressComponentResponse` (`name`, `raw_score`, `weight`, `weighted_score`, `description`)
  - `c_rate_average`, `c_rate_max`, `high_temperature_exposure_percent`
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation or telemetry exists

**Locked Formula:**
```
stress_index = 0.30 × temperature_stress
            + 0.20 × soc_stress
            + 0.20 × power_stress
            + 0.15 × driving_style_stress
            + 0.15 × charging_stress
```

**Stress Categories:**
| Level | Score Range |
|-------|-------------|
| LOW | < 0.25 |
| MODERATE | 0.25 - 0.50 |
| HIGH | 0.50 - 0.75 |
| SEVERE | ≥ 0.75 |

**C-Rate Calculation:**
```
c_rate = |max_power_kw| / battery_capacity_kwh
```

Output includes:
- Overall stress index
- Component stress scores
- C-rate and interpretation
- Temperature stress factors
- Operational stress warnings (not SOH prediction)

---

## 9. What-If Counterfactual Engine

**Endpoint:** `POST /api/v1/intelligence/what-if`

Simulates alternative scenarios starting from the BASE simulation's STARTING state.

- **Path parameters:** none
- **Query parameters:** none
- **Request body:** `WhatIfRequest`
  - `vehicle_id` (string, required)
  - `counterfactual_scenario` (string, required) - scenario to simulate, e.g. `NORMAL_DRIVING`, `AGGRESSIVE_DRIVING`, `FAST_CHARGING`
  - `base_simulation_id` (string, optional) - if omitted, the latest driving simulation is used
  - `duration_minutes` (integer, optional) - inherits from the base simulation if omitted
  - `interval_seconds` (integer, optional) - inherits from the base simulation if omitted
  - `seed` (integer, optional, default `42`)
  - Unknown fields (for example `steps`) are ignored and do not cause an error
- **Response:** `WhatIfResponse`
  - `base_simulation_id`, `base_scenario`, `counterfactual_scenario`, `starting_soc_percent`
  - `base_metrics` and `counterfactual_metrics`: `WhatIfMetricsResponse` (`scenario`, `starting_soc_percent`, `ending_soc_percent`, `energy_consumed_kwh`, `distance_km`, `estimated_range_km` (nullable), `duration_seconds`, `sample_count`)
  - `energy_change_kwh`, `energy_change_percent`, `estimated_range_change_km` (nullable; null for `FAST_CHARGING`)
  - `interpretation`
- **Errors:** 404 if the vehicle or base simulation is not found, no driving simulation exists, or the counterfactual scenario is unknown

**Starting-State Semantics:**
- The counterfactual starts from the state IMMEDIATELY BEFORE the base simulation began, never from the base's first telemetry sample (which is already post-step).
- Fresh-mode base: the canonical vehicle baseline (`VehicleState.from_baseline`, SOC 80.00% for the demo vehicle).
- Continue-mode base: the last telemetry recorded before the base started (`VehicleState.from_telemetry`), falling back to the baseline when none exists, matching the Sprint 1 service.
- The counterfactual runs in fresh mode from that state, at the base's start time, using the same deterministic simulator.

**Key Behavior:**
- Creates in-memory simulation (not persisted; no database writes)
- Starts from the base simulation's nominal starting SOC
- Returns comparison metrics only (no telemetry rows are returned)

---

## 10. Cost Analysis Engine

**Endpoint:** `POST /api/v1/intelligence/cost`

Computes cost-of-driving with a prototype battery wear proxy. Currency is INR.

- **Path parameters:** none
- **Query parameters:** none
- **Request body:** `CostRequest`
  - `vehicle_id` (string, required)
  - `simulation_id` (string, optional) - if omitted, the latest driving simulation is used
  - `electricity_price_per_kwh` (number, required, must be > 0; otherwise 422)
  - `battery_replacement_cost_per_kwh_inr` (number, optional, default `10000.0`)
  - `wear_cost_fraction` (number, optional, default `0.0001`)
- **Response:** `CostResponse`
  - `energy_cost_inr`, `electricity_price_per_kwh`, `energy_used_kwh`
  - `wear_factor` (0-1)
  - `estimated_battery_wear_cost_inr`, `total_operating_cost_inr`
  - `cost_per_km_inr` (nullable), `distance_km`, `duration_seconds`
  - `disclaimer`
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation or telemetry exists; 400 if the analyzer rejects the input; 422 for request validation failures

**Calculation:**
```
energy_cost_inr = net_energy_kwh × electricity_price_per_kwh

normalized_throughput = min(|net_energy_kwh| / usable_battery_capacity_kwh, 1.0)
normalized_stress     = min(battery_stress_score / 100, 1.0)
wear_factor = clamp(0.50 × normalized_throughput
                  + 0.30 × normalized_stress
                  + 0.20 × high_temperature_exposure_ratio, 0, 1)

estimated_battery_wear_cost_inr = wear_factor × wear_cost_fraction
                                  × battery_replacement_cost_per_kwh_inr
                                  × usable_battery_capacity_kwh

total_operating_cost_inr = energy_cost_inr + estimated_battery_wear_cost_inr
cost_per_km_inr = total_operating_cost_inr / distance_km
```

Battery wear is a PROTOTYPE proxy, not a degradation model.

---

## 11. Recommendation Engine

**Endpoint:** `GET /api/v1/intelligence/recommendations/{vehicle_id}`

- **Path parameters:** `vehicle_id` (string)
- **Query parameters:** `simulation_id` (string, optional) - if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `RecommendationsResponse`
  - `recommendations`: list of `RecommendationResponse` (`id`, `title`, `priority`, `reason`, `expected_benefit`, `related_metric`, `impact_score`)
  - `total_generated`, `total_returned` (at most 5)
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation or telemetry exists

Generates actionable recommendations based on analysis results.

**Rules:**
- Maximum 5 recommendations returned (`total_returned` ≤ 5)
- Deduplicated
- Priority ordered (URGENT > HIGH > MEDIUM > LOW)

**Recommendation IDs:**
- REDUCE_SPEED
- SMOOTHER_ACCELERATION
- REDUCE_HIGH_TEMP_EXPOSURE
- REDUCE_HIGH_POWER_LOAD
- USE_REGEN_EFFECTIVELY
- AVOID_DEEP_SOC_SWINGS
- REDUCE_FAST_CHARGING_STRESS
- CHECK_ENERGY_ANOMALY

---

## 12. Explanation Builder

**Endpoint:** No standalone endpoint. The `explanation` object (`ExplanationResponse`: `headline`, `summary`, `key_factors`, `recommendation_summary`, `confidence`) is returned by `GET /api/v1/intelligence/why-range-dropped/{vehicle_id}` and `GET /api/v1/intelligence/summary/{vehicle_id}`.

Template-based natural language generation (no LLM).

**Template Categories:**
- Efficiency explanations
- Range change explanations
- Anomaly descriptions
- Stress level interpretations
- Contributor impact summaries

**Example Output:**
```
"Your efficiency of 5.2 km/kWh is 20% below the baseline of 6.5 km/kWh.
High average speed (105 km/h) is the primary contributor, reducing
efficiency by approximately 15%. Consider reducing speed to improve range."
```

---

## 13. Composite Endpoints (Why-Range and Summary)

**Endpoint:** `GET /api/v1/intelligence/why-range-dropped/{vehicle_id}`

Answers: "Why did my range drop?"

- **Path parameters:** `vehicle_id` (string)
- **Query parameters:** `simulation_id` (string, optional) - observed simulation; if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `WhyRangeDroppedResponse`
  - `vehicle_id`, `observed_simulation_id`, `observed_scenario`
  - `baseline_simulation_id` (nullable), `baseline_match_type`
  - `energy`, `range_estimate`, `contributors`, `anomaly`, `battery_stress`, `recommendations`, `explanation`
  - `confidence` (`HIGH` | `MEDIUM` | `LOW`)
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation exists

**Endpoint:** `GET /api/v1/intelligence/summary/{vehicle_id}`

Returns the complete intelligence summary for a vehicle's driving session.

- **Path parameters:** `vehicle_id` (string)
- **Query parameters:** `simulation_id` (string, optional) - if omitted, the latest driving simulation is used
- **Request body:** none
- **Response:** `IntelligenceSummaryResponse` - same fields and sub-objects as `WhyRangeDroppedResponse`
- **Errors:** 404 if the vehicle or simulation is not found, or no driving simulation exists

The orchestration below is used by both endpoints.

**Orchestration Flow:**
1. Feature extraction
2. Baseline selection
3. Energy analysis
4. Range estimation
5. Contributor analysis
6. Anomaly detection
7. Battery stress analysis
8. Recommendations
9. Explanation building

**Response Structure (abbreviated):**
```json
{
  "vehicle_id": "VG-DEMO-001",
  "observed_simulation_id": "sim-...",
  "observed_scenario": "AGGRESSIVE_DRIVING",
  "baseline_simulation_id": "sim-...",
  "baseline_match_type": "EXACT",
  "energy": { ... },
  "range_estimate": { ... },
  "contributors": { ... },
  "anomaly": { ... },
  "battery_stress": { ... },
  "recommendations": { ... },
  "explanation": { "headline": "...", "summary": "...", "key_factors": [...], "recommendation_summary": "...", "confidence": "..." },
  "confidence": "HIGH"
}
```

---

## 14. API Endpoints Summary

All 10 Sprint 2 intelligence endpoints (prefix `/api/v1/intelligence`):

| Method | Endpoint | Path / Query / Body | Response Model | Description |
|--------|----------|---------------------|----------------|-------------|
| GET | `/energy/{vehicle_id}` | `simulation_id` (query, optional) | `EnergyAnalysisResponse` | Energy analysis |
| GET | `/range/{vehicle_id}` | `simulation_id` (query, optional) | `RangeEstimationResponse` | Range estimation |
| GET | `/contributors/{vehicle_id}` | `simulation_id` (query, optional) | `ContributorAnalysisResponse` | Contributor analysis |
| GET | `/anomaly/{vehicle_id}` | `simulation_id` (query, optional) | `AnomalyDetectionResponse` | Anomaly detection |
| GET | `/battery-stress/{vehicle_id}` | `simulation_id` (query, optional) | `BatteryStressResponse` | Battery stress |
| GET | `/recommendations/{vehicle_id}` | `simulation_id` (query, optional) | `RecommendationsResponse` | Recommendations |
| GET | `/why-range-dropped/{vehicle_id}` | `simulation_id` (query, optional) | `WhyRangeDroppedResponse` | Composite why-range analysis |
| GET | `/summary/{vehicle_id}` | `simulation_id` (query, optional) | `IntelligenceSummaryResponse` | Composite intelligence summary |
| POST | `/what-if` | Body: `WhatIfRequest` | `WhatIfResponse` | Counterfactual simulation |
| POST | `/cost` | Body: `CostRequest` | `CostResponse` | Cost analysis |

**Status codes:**
- 200: Success
- 404: Vehicle, simulation, or driving simulation/telemetry not found (`detail` describes the missing item)
- 400: Cost analyzer rejected the input (`/cost` only)
- 422: Request validation failed (e.g. missing required field, non-positive `electricity_price_per_kwh`)

All intelligence endpoints are side-effect free: they do not write to the database.

---

## 15. Test Results

**Test Files:**
- Sprint 2: `backend/tests/test_intelligence.py`
- Sprint 1: `backend/tests/test_health.py`, `test_simulator.py`, `test_telemetry.py`, `test_vehicle.py`

**Test Totals:**

| Suite | Test Count |
|-------|------------|
| Sprint 1 (`test_health`, `test_simulator`, `test_telemetry`, `test_vehicle`) | **34** |
| Sprint 2 (`test_intelligence`) | **63** |
| **Total** | **97** |

**Execution Summary:**
```
97 passed, 1 warning in 9.47s
```

**Sprint 2 Test Coverage (63 tests):**

| Category | Test Count | Status |
|----------|------------|--------|
| Feature Extraction | 3 | PASS |
| Energy Analysis | 3 | PASS |
| Baseline Selection | 4 | PASS |
| Range Estimation | 3 | PASS |
| Contributor Analysis | 4 | PASS |
| Anomaly Detection | 4 | PASS |
| Battery Stress | 4 | PASS |
| What-If Engine (incl. starting-state semantics) | 11 | PASS |
| Cost Analysis | 5 | PASS |
| Recommendations | 4 | PASS |
| Composite Endpoints (why-range, summary, explanations) | 3 | PASS |
| No-Mutation Verification | 3 | PASS |
| Determinism Verification | 2 | PASS |
| Error Handling | 3 | PASS |
| Hand Calculation | 1 | PASS |
| Pagination Compatibility | 1 | PASS |
| Sprint 1 Regression (within Sprint 2 file) | 5 | PASS |
| **Total Sprint 2** | **63** | **PASS** |

**Sprint 1 Backward Compatibility:**
- All 34 Sprint 1 tests continue to pass
- No breaking changes to existing APIs
- Telemetry simulation behavior unchanged

---

## 16. Manual QA Checklist

| Test Case | Status |
|-----------|--------|
| Energy analysis returns valid efficiency rating | PASS |
| Range estimation uses recent telemetry efficiency | PASS |
| Baseline selection finds EXACT match for same scenario | PASS |
| Baseline returns UNAVAILABLE when no history exists | PASS |
| Anomaly detection uses locked weighted formula | PASS |
| Battery stress uses locked weighted formula | PASS |
| What-if starts from base simulation's starting SOC | PASS |
| Cost analysis includes wear proxy calculation | PASS |
| Recommendations are limited to 5 max | PASS |
| Recommendations are deduplicated by category | PASS |
| Why-range returns comprehensive analysis | PASS |
| All intelligence endpoints are side-effect free | PASS |
| Sprint 1 APIs unchanged and functional | PASS |

---

## 17. Determinism Verification

All intelligence computations are deterministic:

1. **Same Input → Same Output**: Running analysis on identical telemetry produces identical results
2. **No Random Components**: No random number generation in intelligence modules
3. **Locked Formulas**: Anomaly and stress formulas use fixed weights
4. **Reproducible**: Results can be verified by re-running with same data

**Verification Test:**
```python
# Run analysis twice on same simulation
result1 = energy_service.analyze(simulation_id)
result2 = energy_service.analyze(simulation_id)
assert result1 == result2  # Always true
```

---

## 18. Backward Compatibility

Sprint 1 contract fully preserved:

| Feature | Status |
|---------|--------|
| Demo vehicle (VIN: DEMO1234567890123) | Unchanged |
| 5 simulation scenarios | Unchanged |
| Fresh/Continue modes | Unchanged |
| Telemetry pagination | Unchanged |
| Reset functionality | Unchanged |
| Health endpoints | Unchanged |
| Sign conventions | Unchanged |

**No Breaking Changes:**
- All Sprint 1 endpoints remain functional
- Database schema unchanged
- Telemetry format unchanged
- Simulation behavior unchanged

---

## 19. Known Limitations

1. **Synthetic Data Only**: All telemetry is simulated, not from real vehicles
2. **Single Vehicle**: Only supports the demo EV vehicle
3. **No Persistence for What-If**: Counterfactual simulations are in-memory only
4. **Simplified Physics**: Efficiency models are approximations
5. **No External Data**: Weather, traffic, elevation not considered
6. **Battery Stress ≠ SOH**: Stress index is operational, not health prediction
7. **Fixed Parameters**: Electricity rates and costs are hardcoded defaults

---

## 20. Sprint 2 Completion Checklist

| Requirement | Status |
|-------------|--------|
| Intelligence module structure | ✅ Complete |
| Shared feature extraction | ✅ Complete |
| Baseline selection (EXACT/APPROXIMATE/UNAVAILABLE) | ✅ Complete |
| Energy analysis with efficiency rating | ✅ Complete |
| Range estimation with confidence | ✅ Complete |
| Contributor analysis with impact levels | ✅ Complete |
| Anomaly detection with locked formula | ✅ Complete |
| Battery stress with locked formula | ✅ Complete |
| What-if counterfactual engine | ✅ Complete |
| Cost analysis with wear proxy | ✅ Complete |
| Recommendation engine (max 5, deduplicated) | ✅ Complete |
| Explanation builder (template-based) | ✅ Complete |
| Composite why-range orchestrator | ✅ Complete |
| Intelligence API routes | ✅ Complete |
| 60+ Sprint 2 tests | ✅ Complete (63 tests) |
| All tests passing | ✅ Complete (97 passed: 34 Sprint 1 + 63 Sprint 2) |
| Sprint 1 backward compatibility | ✅ Complete |
| Deterministic computations | ✅ Complete |
| Side-effect free endpoints | ✅ Complete |
| No external APIs/LLMs | ✅ Complete |

---

## Post-QA Fix Log

1. **Test-count documentation corrected:** Sprint 1 = 34 tests, Sprint 2 = 63 tests, total = 97 (previously stated as 27 / 66 / 93).
2. **What-if starting state fixed:** the counterfactual previously began from the base's first telemetry sample (post-step, e.g. 79.97% for a NORMAL base whose nominal start is 80.00%). It now begins from the state immediately before the base simulation, using the Sprint 1 authoritative sources (`VehicleState.from_baseline`, `VehicleState.from_telemetry`) and the base's start time.
3. **Shared state construction:** `SimulationEngine` accepts an optional `initial_state` (fresh mode) and copies it so it is never mutated by stepping. The telemetry service's continue-mode state mapping now uses `VehicleState.from_telemetry`. Simulation behavior is unchanged.

**Files modified in this fix:**
- `backend/app/intelligence/what_if.py`
- `backend/app/simulator/engine.py`
- `backend/app/services/telemetry_service.py`
- `backend/tests/test_intelligence.py`
- `backend/SPRINT_2_REPORT.md`

**Unchanged:** anomaly, contributor, battery stress, wear proxy, baseline selection, recommendations, FAST_CHARGING what-if behavior, why-range observed selection, cost contract, confidence framework, and API contracts.

---

## SPRINT 2 COMPLETE

All required features implemented and tested. The deterministic EV intelligence engine is fully functional and ready for hackathon demonstration.

**Files Created:**
- `backend/app/intelligence/__init__.py`
- `backend/app/intelligence/config.py`
- `backend/app/intelligence/features.py`
- `backend/app/intelligence/baseline.py`
- `backend/app/intelligence/energy.py`
- `backend/app/intelligence/range_estimator.py`
- `backend/app/intelligence/contributors.py`
- `backend/app/intelligence/anomaly.py`
- `backend/app/intelligence/battery_stress.py`
- `backend/app/intelligence/what_if.py`
- `backend/app/intelligence/cost.py`
- `backend/app/intelligence/recommendations.py`
- `backend/app/intelligence/explanation.py`
- `backend/app/intelligence/orchestrator.py`
- `backend/app/schemas/intelligence.py`
- `backend/app/api/routes_intelligence.py`
- `backend/tests/test_intelligence.py`

**Files Modified:**
- `backend/app/api/__init__.py`
- `backend/app/main.py`

---

*Report generated for iQOO Hackathon 2026 Mobility Grand Finale*
