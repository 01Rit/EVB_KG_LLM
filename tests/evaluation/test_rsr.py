"""Tests for RSR: rank-sum ratio computation and grading."""
import pytest
from src.evaluation.rsr import (
    compute_dimension_rsr,
    compute_total_rsr,
    compute_dynamic_thresholds,
)


class TestDimensionRSR:
    def test_single_version(self):
        scores = [[0.8, 0.6, 0.9]]
        weights = [1.0, 1.0, 1.0]
        rsr = compute_dimension_rsr(scores, weights)
        assert len(rsr) == 1
        assert 0 < rsr[0] <= 1

    def test_three_versions(self):
        scores = [
            [0.9, 0.5, 0.8],
            [0.3, 0.9, 0.4],
            [0.6, 0.7, 0.6],
        ]
        weights = [1.0, 1.0, 1.0]
        rsr = compute_dimension_rsr(scores, weights)
        assert len(rsr) == 3
        assert rsr[0] != rsr[1]

    def test_weights_affect_rsr(self):
        scores = [
            [0.9, 0.3],
            [0.3, 0.9],
        ]
        rsr_high_first = compute_dimension_rsr(scores, [2.0, 1.0])
        rsr_high_second = compute_dimension_rsr(scores, [1.0, 2.0])
        assert rsr_high_first[0] > rsr_high_second[0]


class TestTotalRSR:
    def test_hierarchical_synthesis(self):
        dim_rsrs = [
            [0.8, 0.6, 0.7],
            [0.5, 0.9, 0.4],
            [0.7, 0.3, 0.8],
        ]
        dim_weights = [0.4, 0.35, 0.25]
        total = compute_total_rsr(dim_rsrs, dim_weights)
        assert len(total) == 3
        assert all(0 < r <= 1 for r in total)


class TestDynamicThresholds:
    def test_five_versions(self):
        total_rsrs = [0.3, 0.5, 0.6, 0.7, 0.9]
        thresholds = compute_dynamic_thresholds(total_rsrs)
        assert thresholds["excellent"] > thresholds["good"]
        assert thresholds["good"] > thresholds["qualified"]

    def test_two_versions_minimum(self):
        total_rsrs = [0.4, 0.8]
        thresholds = compute_dynamic_thresholds(total_rsrs)
        assert "excellent" in thresholds
