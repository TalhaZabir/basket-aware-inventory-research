"""Create dependency-free SVG figures for the results section."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
OUT = ROOT / "results"
COLORS = {
    "deterministic_7d": "#4C78A8",
    "low_variance_normal": "#F58518",
    "high_variance_normal": "#54A24B",
    "right_skewed_discrete": "#E45756",
}


def esc(value: object) -> str:
    return html.escape(str(value))


def svg_start(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#222}.axis{stroke:#555;stroke-width:1}.grid{stroke:#ddd;stroke-width:1}.label{font-size:12px}.small{font-size:10px}</style>',
        f'<text x="{width/2:.1f}" y="28" text-anchor="middle" font-size="18" font-weight="bold">{esc(title)}</text>',
    ]


def add_axes(parts: list[str], left: float, top: float, width: float, height: float, x_label: str, y_label: str, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
    parts.append(f'<line class="axis" x1="{left}" y1="{top+height}" x2="{left+width}" y2="{top+height}"/><line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top+height}"/>')
    for tick in range(5):
        frac = tick / 4
        x = left + frac * width
        y = top + height - frac * height
        xv = x_min + frac * (x_max - x_min)
        yv = y_min + frac * (y_max - y_min)
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+height}"/><text class="small" x="{x:.1f}" y="{top+height+18:.1f}" text-anchor="middle">{xv:.1f}</text>')
        parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left+width}" y2="{y:.1f}"/><text class="small" x="{left-8:.1f}" y="{y+4:.1f}" text-anchor="end">{yv:.2f}</text>')
    parts.append(f'<text class="label" x="{left+width/2:.1f}" y="{top+height+42:.1f}" text-anchor="middle">{esc(x_label)}</text>')
    parts.append(f'<text class="label" x="{left-48:.1f}" y="{top+height/2:.1f}" text-anchor="middle" transform="rotate(-90 {left-48:.1f} {top+height/2:.1f})">{esc(y_label)}</text>')


def histogram(values: list[float], bins: int, x_min: float, x_max: float) -> list[int]:
    counts = [0] * bins
    span = max(x_max - x_min, 1e-9)
    for value in values:
        clipped = min(max(value, x_min), x_max - 1e-9)
        index = int((clipped - x_min) / span * bins)
        counts[max(0, min(bins - 1, index))] += 1
    return counts


def make_cost_vs_penalty() -> None:
    summary = pd.read_csv(OUT / "inventory_summary.csv")
    summary["short_policy"] = summary["policy"].str.extract(r"^(P[1-4])")
    pivot = summary.pivot_table(index=["scenario_id", "lead_time_distribution", "shortage_penalty_per_unit"], columns="short_policy", values="total_cost_mean").reset_index()
    values = [float(v) for v in (pivot["P3"] - pivot["P1"]).tolist() + (pivot["P4"] - pivot["P2"]).tolist()]
    x_min, x_max = 1.0, 11.0
    y_min, y_max = min(values) * 1.08, max(values) * 1.08
    parts = svg_start(1000, 600, "Simulated cost differences across shortage-penalty scenarios")
    left, top, width, height = 95, 65, 790, 390
    add_axes(parts, left, top, width, height, "Shortage penalty p", "Basket-aware minus independent cost", x_min, x_max, y_min, y_max)
    sx = lambda x: left + (x-x_min)/(x_max-x_min)*width
    sy = lambda y: top + height - (y-y_min)/(y_max-y_min)*height
    parts.append(f'<line x1="{left}" y1="{sy(0):.1f}" x2="{left+width}" y2="{sy(0):.1f}" stroke="#333" stroke-dasharray="5,4"/>')
    for row in pivot.itertuples():
        x, color = sx(float(row.shortage_penalty_per_unit)), COLORS[row.lead_time_distribution]
        parts.append(f'<circle cx="{x:.1f}" cy="{sy(float(row.P3-row.P1)):.1f}" r="5" fill="{color}"/><rect x="{x-5:.1f}" y="{sy(float(row.P4-row.P2))-5:.1f}" width="10" height="10" fill="{color}"/>')
    legend_y = 510
    parts.append(f'<circle cx="100" cy="{legend_y}" r="5" fill="#222"/><text class="small" x="112" y="{legend_y+4}">P3 − P1</text><rect x="190" y="{legend_y-5}" width="10" height="10" fill="#222"/><text class="small" x="208" y="{legend_y+4}">P4 − P2</text>')
    x = 315
    for family, color in COLORS.items():
        parts.append(f'<rect x="{x}" y="{legend_y-5}" width="10" height="10" fill="{color}"/><text class="small" x="{x+16}" y="{legend_y+4}">{esc(family.replace("_", " "))}</text>')
        x += 160
    parts.append('</svg>')
    (OUT / "cost_vs_penalty.svg").write_text("\n".join(parts), encoding="utf-8")


def make_basket_size() -> None:
    lines = pd.read_csv(ROOT / "data" / "processed" / "uci_transaction_lines_clean.csv", dtype={"invoice_id": "string"})
    sizes = lines.groupby("invoice_id").size().astype(float)
    x_min, x_max = 0.0, float(sizes.quantile(0.99))
    counts = histogram(sizes.tolist(), 35, x_min, x_max)
    parts = svg_start(1000, 600, "Observed basket-size distribution")
    left, top, width, height = 95, 65, 790, 390
    add_axes(parts, left, top, width, height, "Retained transaction lines per invoice (99th percentile shown)", "Number of baskets", x_min, x_max, 0, max(counts)*1.1)
    bar_w = width / len(counts)
    for i, count in enumerate(counts):
        h = count / max(counts) * height
        parts.append(f'<rect x="{left+i*bar_w:.1f}" y="{top+height-h:.1f}" width="{max(1,bar_w-1):.1f}" height="{h:.1f}" fill="#4C78A8" opacity="0.85"/>')
    for value, color, label in [(float(sizes.mean()), "#E45756", f"Mean {sizes.mean():.1f}"), (float(sizes.median()), "#F58518", f"Median {sizes.median():.0f}")]:
        x = left + value / x_max * width
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+height}" stroke="{color}" stroke-width="2"/><text class="small" x="{x+5:.1f}" y="{top+18}">{label}</text>')
    parts.append('</svg>')
    (OUT / "basket_size_distribution.svg").write_text("\n".join(parts), encoding="utf-8")


def make_graph_summary() -> None:
    edges = pd.read_csv(ROOT / "data" / "processed" / "uci_copurchase_edges_train_only.csv", dtype={"stock_code_a": "string", "stock_code_b": "string"})
    degree = pd.concat([edges["stock_code_a"], edges["stock_code_b"]]).value_counts().astype(float)
    conditional = pd.concat([edges["p_b_given_a"], edges["p_a_given_b"]]).astype(float)
    panels = [(degree.tolist(), 0, float(degree.quantile(0.99)), "Incident retained pairs per product", "Training graph degree", "#54A24B"), (conditional.tolist(), 0, 1, "Directed conditional probability", "Conditional co-purchase scores", "#F58518")]
    parts = svg_start(1200, 650, "Training-only co-purchase graph summary")
    parts.append('<text x="600" y="52" text-anchor="middle" class="small">1,576,291 retained pairs; 29.3% of possible pairs among 3,279 supported products</text>')
    for panel, (values, x_min, x_max, xlabel, title, color) in enumerate(panels):
        left, top, width, height = 85 + panel*560, 85, 460, 400
        counts = histogram(values, 32, x_min, x_max)
        add_axes(parts, left, top, width, height, xlabel, title, x_min, x_max, 0, max(counts)*1.1)
        bar_w = width / len(counts)
        for i, count in enumerate(counts):
            h = count / max(counts) * height
            parts.append(f'<rect x="{left+i*bar_w:.1f}" y="{top+height-h:.1f}" width="{max(1,bar_w-1):.1f}" height="{h:.1f}" fill="{color}" opacity="0.85"/>')
    parts.append('</svg>')
    (OUT / "graph_summary.svg").write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    make_cost_vs_penalty()
    make_basket_size()
    make_graph_summary()
    print("created cost_vs_penalty.svg, basket_size_distribution.svg, graph_summary.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
