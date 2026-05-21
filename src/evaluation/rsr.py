"""RSR: Rank-Sum Ratio computation for batch evaluation."""
import numpy as np
from scipy.special import ndtri


def compute_dimension_rsr(
    scores: list[list[float]],
    weights: list[float],
) -> list[float]:
    """Compute RSR_z for each version within one dimension.

    Args:
        scores: scores[version_idx][rule_idx] = fuzzy match score
        weights: weight per rule

    Returns:
        List of RSR values, one per version.
    """
    l = len(scores)
    n = len(scores[0])
    weights_arr = np.array(weights)
    norm_weights = weights_arr / weights_arr.sum()

    score_matrix = np.array(scores)
    ranks = np.zeros_like(score_matrix)
    for j in range(n):
        col = score_matrix[:, j]
        ranks[:, j] = np.argsort(np.argsort(col)) + 1

    rsr = np.zeros(l)
    for i in range(l):
        rsr[i] = np.sum(norm_weights * ranks[i, :]) / l

    return rsr.tolist()


def compute_total_rsr(
    dim_rsrs: list[list[float]],
    dim_weights: list[float],
) -> list[float]:
    """Hierarchical synthesis: rank dimension RSRs, then compute total RSR."""
    num_dims = len(dim_rsrs)
    num_versions = len(dim_rsrs[0])
    dim_weights_arr = np.array(dim_weights)
    norm_weights = dim_weights_arr / dim_weights_arr.sum()

    rank_matrix = np.zeros((num_versions, num_dims))
    for d in range(num_dims):
        col = np.array(dim_rsrs[d])
        rank_matrix[:, d] = np.argsort(np.argsort(col)) + 1

    total = np.zeros(num_versions)
    for i in range(num_versions):
        total[i] = np.sum(norm_weights * rank_matrix[i, :]) / num_versions

    return total.tolist()


def compute_dynamic_thresholds(total_rsrs: list[float]) -> dict:
    """Compute grade thresholds using probit regression.

    P = inverse_normal(cumulative_freq) + 5  (standard probit transform, +5 offset)
    RSR_fit = a + b * P
    """
    l = len(total_rsrs)
    sorted_rsrs = sorted(total_rsrs)

    cum_freqs = []
    for i in range(l):
        if i < l - 1:
            p = (i + 1) / l
        else:
            p = 1 - 1 / (4 * l)  # correction for last
        cum_freqs.append(p)

    probits = [ndtri(p) + 5.0 for p in cum_freqs]

    b, a = np.polyfit(probits, sorted_rsrs, 1)

    return {
        "excellent": float(a + b * 6.5),
        "good": float(a + b * 5.0),
        "qualified": float(a + b * 3.5),
        "regression": {"a": float(a), "b": float(b)},
    }
