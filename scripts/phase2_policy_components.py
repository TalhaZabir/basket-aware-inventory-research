"""Training-only graph and buffer construction for Phase 2.

All objects returned by this module are built from the training period. The
buffers are in item units and are passed to the simulator through its explicit
``basket_buffer`` argument.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


Z = 1.645
DEFAULT_MIN_PAIR_COUNT = 5
DEFAULT_TOP_K = 5


def _index_edges(edges: pd.DataFrame, products: np.ndarray) -> pd.DataFrame:
    index = {str(product): i for i, product in enumerate(products)}
    frame = edges.copy()
    frame["a"] = frame["stock_code_a"].map(index)
    frame["b"] = frame["stock_code_b"].map(index)
    frame = frame.dropna(subset=["a", "b"]).copy()
    frame["a"] = frame["a"].astype(int)
    frame["b"] = frame["b"].astype(int)
    return frame


def default_edges(root: Path, products: np.ndarray, min_pair_count: int = DEFAULT_MIN_PAIR_COUNT) -> pd.DataFrame:
    path = root / "data" / "processed" / "uci_copurchase_edges_train_only.csv"
    edges = pd.read_csv(path, dtype={"stock_code_a": "string", "stock_code_b": "string"})
    edges = edges.loc[edges["co_purchase_count"] >= min_pair_count]
    return _index_edges(edges, products)


def _basket_edges(lines: pd.DataFrame, products: np.ndarray, label_permutation: np.ndarray | None = None, min_pair_count: int = DEFAULT_MIN_PAIR_COUNT) -> pd.DataFrame:
    index = {str(product): i for i, product in enumerate(products)}
    lines = lines.loc[lines["stock_code"].isin(index)].copy()
    lines["product_idx"] = lines["stock_code"].map(index).astype(int)
    if label_permutation is not None:
        lines["product_idx"] = label_permutation[lines["product_idx"].to_numpy()]
    pair_counts: dict[tuple[int, int], int] = {}
    for _invoice, frame in lines.groupby("invoice_id", sort=False):
        items = sorted(set(frame["product_idx"].tolist()))
        for a, b in combinations(items, 2):
            pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1
    rows = [{"a": a, "b": b, "co_purchase_count": count} for (a, b), count in pair_counts.items() if count >= min_pair_count]
    result = pd.DataFrame(rows, columns=["a", "b", "co_purchase_count"])
    if result.empty:
        return result
    total_a = result.groupby("a")["co_purchase_count"].sum()
    total_b = result.groupby("b")["co_purchase_count"].sum()
    result["p_b_given_a"] = result["co_purchase_count"] / result["a"].map(total_a)
    result["p_a_given_b"] = result["co_purchase_count"] / result["b"].map(total_b)
    return result


def training_lines(root: Path, end_date: str) -> pd.DataFrame:
    lines = pd.read_csv(root / "data" / "processed" / "uci_transaction_lines_clean.csv", dtype={"invoice_id": "string", "stock_code": "string"})
    lines["invoice_date"] = pd.to_datetime(lines["invoice_date"])
    return lines.loc[lines["invoice_date"] <= pd.Timestamp(end_date)].copy()


def stale_edges(root: Path, products: np.ndarray, end_date: str = "2010-12-27", min_pair_count: int = DEFAULT_MIN_PAIR_COUNT) -> pd.DataFrame:
    return _basket_edges(training_lines(root, end_date), products, min_pair_count=min_pair_count)


def shuffled_basket_edges(root: Path, products: np.ndarray, seed: int = 20261020, min_pair_count: int = DEFAULT_MIN_PAIR_COUNT) -> pd.DataFrame:
    lines = training_lines(root, "2011-06-27")
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(len(products))
    return _basket_edges(lines, products, label_permutation=permutation, min_pair_count=min_pair_count)


def rewired_edges(edges: pd.DataFrame, seed: int = 20261020) -> pd.DataFrame:
    """Re-pair endpoint stubs so the node degree sequence is retained.

    Parallel edges are retained as weighted edge records. The original edge
    count multiset is permuted independently, so the edge-weight distribution
    is preserved while the original endpoint relationships are removed.
    """
    if edges.empty:
        return edges.copy()
    rng = np.random.default_rng(seed)
    stubs = np.concatenate([edges["a"].to_numpy(), edges["b"].to_numpy()])
    rng.shuffle(stubs)
    a = stubs[: len(edges)].copy()
    b = stubs[len(edges):].copy()
    for i in range(len(edges)):
        if a[i] == b[i]:
            swap = (i + 1) % len(edges)
            b[i], b[swap] = b[swap], b[i]
    counts = edges["co_purchase_count"].to_numpy(copy=True)
    rng.shuffle(counts)
    rewired = pd.DataFrame({"a": a, "b": b, "co_purchase_count": counts})
    total_a = rewired.groupby("a")["co_purchase_count"].sum()
    total_b = rewired.groupby("b")["co_purchase_count"].sum()
    rewired["p_b_given_a"] = rewired["co_purchase_count"] / rewired["a"].map(total_a)
    rewired["p_a_given_b"] = rewired["co_purchase_count"] / rewired["b"].map(total_b)
    return rewired


def edge_buffer(edges: pd.DataFrame, n_products: int, risk_units: np.ndarray, top_k: int = DEFAULT_TOP_K) -> np.ndarray:
    buffer = np.zeros(n_products, dtype=float)
    if edges.empty:
        return buffer
    directed: dict[int, list[tuple[float, float, int]]] = {}
    for row in edges.itertuples(index=False):
        a, b = int(row.a), int(row.b)
        count = float(row.co_purchase_count)
        p_ab = float(getattr(row, "p_b_given_a", 0.0))
        p_ba = float(getattr(row, "p_a_given_b", 0.0))
        directed.setdefault(a, []).append((p_ab, count, b))
        directed.setdefault(b, []).append((p_ba, count, a))
    for a, values in directed.items():
        chosen = sorted(values, key=lambda x: (x[0], x[1]), reverse=True)[:top_k]
        weight_total = sum(value[1] for value in chosen)
        if weight_total <= 0:
            continue
        buffer[a] = sum((count / weight_total) * probability * risk_units[partner] for probability, count, partner in chosen)
    return buffer


def scale_to_total(values: np.ndarray, total: float) -> np.ndarray:
    values = np.maximum(np.asarray(values, dtype=float), 0.0)
    current = float(values.sum())
    if current <= 0 or total <= 0:
        return np.zeros_like(values)
    return values * (total / current)


def training_volume(root: Path, products: np.ndarray, end_date: str = "2011-06-27") -> np.ndarray:
    lines = training_lines(root, end_date)
    index = {str(product): i for i, product in enumerate(products)}
    lines = lines.loc[lines["stock_code"].isin(index)].copy()
    lines["idx"] = lines["stock_code"].map(index).astype(int)
    return lines.groupby("idx")["quantity"].sum().reindex(range(len(products)), fill_value=0.0).to_numpy(dtype=float)


def basket_coverage_score(root: Path, products: np.ndarray, end_date: str = "2011-06-27") -> np.ndarray:
    lines = training_lines(root, end_date)
    index = {str(product): i for i, product in enumerate(products)}
    lines = lines.loc[lines["stock_code"].isin(index)].copy()
    lines["idx"] = lines["stock_code"].map(index).astype(int)
    score = np.zeros(len(products), dtype=float)
    for _invoice, frame in lines.groupby("invoice_id", sort=False):
        items = sorted(set(frame["idx"].tolist()))
        if not items:
            continue
        contribution = 1.0 / len(items)
        score[items] += contribution
    return score


def buffers_from_graphs(root: Path, products: np.ndarray, residual_std: np.ndarray, safety_multiplier: float, default: pd.DataFrame, stale: pd.DataFrame, shuffled: pd.DataFrame, rewired: pd.DataFrame, tau: float = 0.75) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    # The Phase 1 multiplier calibrates the independent base-stock policy. The
    # incremental pair buffer uses the uninflated residual risk so its mass can
    # be compared with an inventory-matched independent control.
    risk = Z * np.maximum(residual_std, 0.25)
    pa1 = edge_buffer(default, len(products), risk)
    total = float(pa1.sum())
    coverage = scale_to_total(basket_coverage_score(root, products), total)
    popularity = scale_to_total(training_volume(root, products), total)
    threshold = float(np.quantile(pa1[pa1 > 0], tau)) if np.any(pa1 > 0) else 0.0
    pa3 = scale_to_total(np.where(pa1 >= threshold, pa1, 0.0), total)
    buffers = {
        "PA1": pa1,
        "PA2": coverage,
        "PA3": pa3,
        "C2": scale_to_total(edge_buffer(rewired, len(products), risk), total),
        "C3": scale_to_total(edge_buffer(shuffled, len(products), risk), total),
        "C4": popularity,
        "C5": scale_to_total(edge_buffer(stale, len(products), risk), total),
    }
    metadata = {
        "default_edges": int(len(default)),
        "rewired_edges": int(len(rewired)),
        "shuffled_edges": int(len(shuffled)),
        "stale_edges": int(len(stale)),
        "pa1_buffer_total": total,
        "pa3_tau_quantile": tau,
        "pa3_threshold": threshold,
        "all_buffer_totals_equal": bool(max(abs(float(value.sum()) - total) for value in buffers.values()) < 1e-6),
    }
    return buffers, metadata


def build_buffers(root: Path, products: np.ndarray, residual_std: np.ndarray, safety_multiplier: float, tau: float = 0.75, seed: int = 20261020) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    default = default_edges(root, products)
    stale = stale_edges(root, products)
    shuffled = shuffled_basket_edges(root, products, seed=seed)
    rewired = rewired_edges(default, seed=seed)
    return buffers_from_graphs(root, products, residual_std, safety_multiplier, default, stale, shuffled, rewired, tau=tau)
