"""VehicleGPT Intelligence Engine - Sprint 2.

This module provides deterministic vehicle intelligence analysis including:
- Energy analysis
- Range estimation
- Baseline comparison
- Contributor analysis
- Anomaly detection
- Battery stress analysis
- Cost-of-driving analysis
- Recommendations
- Explanations
- What-if counterfactual simulation
"""

from app.intelligence.config import IntelligenceConfig
from app.intelligence.features import FeatureExtractor, TelemetryFeatures
from app.intelligence.energy import EnergyAnalyzer
from app.intelligence.baseline import BaselineSelector, BaselineMatchType
from app.intelligence.range_estimator import RangeEstimator
from app.intelligence.contributors import ContributorAnalyzer
from app.intelligence.anomaly import AnomalyDetector
from app.intelligence.battery_stress import BatteryStressAnalyzer
from app.intelligence.what_if import WhatIfEngine
from app.intelligence.cost import CostAnalyzer
from app.intelligence.recommendations import RecommendationEngine
from app.intelligence.explanation import ExplanationBuilder
from app.intelligence.orchestrator import IntelligenceOrchestrator

__all__ = [
    "IntelligenceConfig",
    "FeatureExtractor",
    "TelemetryFeatures",
    "EnergyAnalyzer",
    "BaselineSelector",
    "BaselineMatchType",
    "RangeEstimator",
    "ContributorAnalyzer",
    "AnomalyDetector",
    "BatteryStressAnalyzer",
    "WhatIfEngine",
    "CostAnalyzer",
    "RecommendationEngine",
    "ExplanationBuilder",
    "IntelligenceOrchestrator",
]
