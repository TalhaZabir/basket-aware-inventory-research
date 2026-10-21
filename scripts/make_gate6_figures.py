"""Create the three manuscript figures added for Gate 6."""
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
FONT = "C:/Windows/Fonts/arial.ttf"
if not Path(FONT).exists():
    FONT = "C:/Windows/Fonts/calibri.ttf"


def font(size: int):
    return ImageFont.truetype(FONT, size)


def canvas(title: str):
    im = Image.new("RGB", (1200, 760), "white")
    dr = ImageDraw.Draw(im)
    dr.text((600, 25), title, fill="#222222", font=font(24), anchor="ma")
    return im, dr


def axes(dr, x0=205, y0=95, x1=1120, y1=670):
    dr.line((x0, y1, x1, y1), fill="#555555", width=2)
    dr.line((x0, y0, x0, y1), fill="#555555", width=2)


def forest() -> None:
    d = pd.read_csv(OUT / "phase3_scenario_contrast_summary.csv")
    d = d[d.contrast.isin(["PA1_minus_C4", "PA1_minus_C1"])].copy()
    d["label"] = d.scenario_id + "  " + d.contrast.str.replace("PA1_minus_", "PA1 minus ", regex=False)
    d = d.sort_values(["scenario_id", "contrast"])
    im, dr = canvas("Figure 5. Scenario-level matched contrasts")
    axes(dr)
    xmin, xmax = -0.04, 0.04
    def sx(v): return 205 + (v-xmin)/(xmax-xmin)*915
    dr.line((sx(0),95,sx(0),670), fill="#888888", width=1)
    for j, (_, r) in enumerate(d.iterrows()):
        y = 105 + j*24
        color = "#1f77b4" if r.contrast == "PA1_minus_C4" else "#d95f02"
        dr.text((195,y), r.label, fill="#222222", font=font(15), anchor="ra")
        lo, hi, m = r.item_fill_difference_ci95_low, r.item_fill_difference_ci95_high, r.item_fill_difference_mean
        dr.line((sx(lo),y,sx(hi),y), fill=color, width=3)
        dr.ellipse((sx(m)-5,y-5,sx(m)+5,y+5), fill=color)
    dr.text((660,705), "PA1 minus control in item fill rate", fill="#222222", font=font(17), anchor="ma")
    im.save(OUT / "forest_plot.png")


def strata() -> None:
    d = pd.read_csv(OUT / "gate2_pair_regime_summary.csv")
    d = d[d.metric == "item_fill_rate"].copy()
    labels = ["Low-popularity\n/high-lift", "High-popularity\n/high-lift"]
    order = ["low_pop_high_lift", "high_pop_high_lift"]
    d["order"] = d.regime.map({x: i for i, x in enumerate(order)})
    d = d.sort_values("order")
    im, dr = canvas("Figure 5. Graph signal by popularity stratum")
    axes(dr)
    ymin, ymax = -0.10, 0.12
    def sy(v): return 670 - (v-ymin)/(ymax-ymin)*575
    dr.line((205,sy(0),1120,sy(0)), fill="#888888", width=1)
    for j, (_, r) in enumerate(d.iterrows()):
        x = 470 + j*390
        lo, hi, m = r.ci95_low, r.ci95_high, r.mean_difference
        dr.line((x,sy(lo),x,sy(hi)), fill="#1f77b4", width=5)
        dr.ellipse((x-8,sy(m)-8,x+8,sy(m)+8), fill="#1f77b4")
        dr.text((x,700), labels[j], fill="#222222", font=font(16), anchor="ma")
        dr.text((x,sy(m)-25), f"{m:+.3f}", fill="#222222", font=font(16), anchor="ma")
    dr.text((660,735), "PA1 minus C4 item fill rate (95% replication interval)", fill="#222222", font=font(17), anchor="ma")
    im.save(OUT / "mechanism_strata.png")


def replication() -> None:
    uci = pd.read_csv(OUT / "phase3_cluster_pooled_summary.csv")
    uci = uci[uci.contrast == "PA1_minus_C4"].iloc[0]
    dh = pd.read_csv(OUT / "dunnhumby_gate3_contrast_summary.csv")
    dh = dh[(dh.contrast == "PA1_minus_C4") & (dh.metric == "item_fill_rate")].iloc[0]
    labels = ["UCI Online Retail II", "dunnhumby Complete Journey"]
    means = [uci.item_fill_difference_cluster_mean, dh.mean_difference]
    lows = [uci.item_fill_difference_cluster_ci95_low, dh.ci95_low]
    highs = [uci.item_fill_difference_cluster_ci95_high, dh.ci95_high]
    im, dr = canvas("Figure 7. External pipeline stress check")
    axes(dr)
    ymin, ymax = -1.0, 0.1
    def sy(v): return 670 - (v-ymin)/(ymax-ymin)*575
    dr.line((205,sy(0),1120,sy(0)), fill="#888888", width=1)
    for j, (label,m,lo,hi) in enumerate(zip(labels,means,lows,highs)):
        x = 470 + j*390
        dr.line((x,sy(lo),x,sy(hi)), fill="#1f77b4", width=5)
        dr.ellipse((x-8,sy(m)-8,x+8,sy(m)+8), fill="#1f77b4")
        dr.text((x,700), label, fill="#222222", font=font(16), anchor="ma")
        dr.text((x,sy(m)-25), f"{m:+.3f}", fill="#222222", font=font(16), anchor="ma")
    dr.text((660,735), "PA1 minus C4 item fill rate", fill="#222222", font=font(17), anchor="ma")
    im.save(OUT / "external_pipeline_check.png")


if __name__ == "__main__":
    forest()
    strata()
    replication()
    print("Gate 6 figures written to", OUT)
