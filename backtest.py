"""
Room A utilization forecast: reproducible backtest and charts.

Reads the anonymized CSVs in ../data and:
  1. Backtests the weekly forecast: predict Year 3 from Years 1-2, score against Year 3 actuals,
     and compare with a naive "same as last year" forecast.
  2. Backtests the hourly (8 AM-5 PM, Mon-Fri) usage pattern the same way.
  3. Builds the Year 4 hourly forecast (weighted 20/30/50) and saves heatmaps to ../images.

Run:  python analysis/backtest.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA, IMG = ROOT / "data", ROOT / "images"
IMG.mkdir(exist_ok=True)

QUARTERS = ["Fall", "Winter", "Spring", "Summer"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
HOURS = list(range(8, 17))                      # hour slots 8-9 ... 4-5 PM
HOUR_LABELS = ["8", "9", "10", "11", "12", "1", "2", "3", "4"]
BT_WEIGHTS = {"Year 1": 0.4, "Year 2": 0.6}      # backtest: forecast Year 3 from Years 1-2
LIVE_WEIGHTS = {"Year 1": 0.2, "Year 2": 0.3, "Year 3": 0.5}
BUSY = 0.5                                       # an hour slot is "busy" if >= 50% booked


def wape(actual, forecast):
    return np.abs(actual - forecast).sum() / actual.sum()


# ---------- 1. Weekly backtest ----------
weekly = pd.read_csv(DATA / "weekly_bookings.csv")
lengths = pd.read_csv(DATA / "sample_week_booking_lengths.csv")
lengths["avg_hours"] = lengths["hours_in_sample"] / lengths["bookings_in_sample"]
avg_len = lengths.set_index(["year", "quarter"])["avg_hours"]

for i, y in enumerate(["Year 1", "Year 2", "Year 3"], start=1):
    weekly[f"hours{i}"] = weekly[f"year{i}"] * weekly["quarter"].map(lambda q, y=y: avg_len[(y, q)])

weekly["model"] = BT_WEIGHTS["Year 1"] * weekly.year1 + BT_WEIGHTS["Year 2"] * weekly.year2
weekly["naive"] = weekly.year2
weekly["model_hrs"] = BT_WEIGHTS["Year 1"] * weekly.hours1 + BT_WEIGHTS["Year 2"] * weekly.hours2
weekly["naive_hrs"] = weekly.hours2

rows = [
    ("Weekly bookings WAPE", wape(weekly.year3, weekly.model), wape(weekly.year3, weekly.naive)),
    ("Weekly hours WAPE", wape(weekly.hours3, weekly.model_hrs), wape(weekly.hours3, weekly.naive_hrs)),
    ("Year 3 total bookings bias", weekly.model.sum() / weekly.year3.sum() - 1, weekly.naive.sum() / weekly.year3.sum() - 1),
    ("Year 3 total hours bias", weekly.model_hrs.sum() / weekly.hours3.sum() - 1, weekly.naive_hrs.sum() / weekly.hours3.sum() - 1),
]

# ---------- 2. Hourly usage grids from the booking log ----------
log = pd.read_csv(DATA / "booking_log_sample_weeks.csv")
to_h = lambda t: int(t[:2]) + int(t[3:]) / 60
log["s"], log["e"] = log.start.map(to_h), log.end.map(to_h)


def usage_grid(year, quarter, n_weeks=1):
    """Share of each hour booked (0-1), days x hours, capped at 100% for overlaps."""
    sub = log[(log.year == year) & (log.quarter == quarter)]
    g = np.zeros((len(DAYS), len(HOURS)))
    for di, d in enumerate(DAYS):
        for b in sub[sub.day == d].itertuples():
            for hi, h in enumerate(HOURS):
                g[di, hi] += max(0.0, min(b.e, h + 1) - max(b.s, h))
    return np.minimum(1, g / n_weeks)


grids = {(y, q): usage_grid(y, q) for y in ["Year 1", "Year 2", "Year 3"] for q in QUARTERS}
err_m, err_n, ok_m, ok_n = [], [], [], []
for q in QUARTERS:
    actual = grids[("Year 3", q)]
    model = BT_WEIGHTS["Year 1"] * grids[("Year 1", q)] + BT_WEIGHTS["Year 2"] * grids[("Year 2", q)]
    naive = grids[("Year 2", q)]
    err_m += list(np.abs(actual - model).ravel()); err_n += list(np.abs(actual - naive).ravel())
    T = BUSY - 1e-6
    ok_m += list(((model >= T) == (actual >= T)).ravel()); ok_n += list(((naive >= T) == (actual >= T)).ravel())
rows += [("Hourly mean abs error", np.mean(err_m), np.mean(err_n)),
         ("Hourly busy/open called correctly", np.mean(ok_m), np.mean(ok_n))]

print(f"{'Metric':38s} {'Model':>8s} {'Naive':>8s}")
for name, m, n in rows:
    print(f"{name:38s} {m:8.1%} {n:8.1%}")

# ---------- 3. Charts ----------
x = np.arange(len(weekly))
plt.figure(figsize=(12, 4))
plt.plot(x, weekly.year3, label="Actual (Year 3)", lw=2, color="#8C1515")
plt.plot(x, weekly.model, label="Model (Years 1-2, 40/60)", lw=1.6, color="#2E6F9E")
plt.plot(x, weekly.naive, label="Naive (same as last year)", lw=1.2, ls="--", color="#999999")
for q in QUARTERS[1:]:
    plt.axvline(weekly.index[weekly.quarter == q][0] - 0.5, color="#dddddd", lw=1)
plt.xticks([weekly.index[weekly.quarter == q][0] + 4 for q in QUARTERS], QUARTERS)
plt.ylabel("Bookings per week"); plt.title("Backtest: weekly bookings, Year 3 actual vs forecast")
plt.legend(frameon=False); plt.tight_layout(); plt.savefig(IMG / "backtest_weekly.png", dpi=150); plt.close()

fig, axes = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
for ax, q in zip(axes, QUARTERS):
    live = sum(w * grids[(y, q)] for y, w in LIVE_WEIGHTS.items())
    im = ax.imshow(np.minimum(1, live), cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(HOURS)), HOUR_LABELS); ax.set_yticks(range(len(DAYS)), DAYS)
    ax.set_title(f"{q}: avg {live.mean():.0%} booked"); ax.set_xlabel("Hour starting")
    for di in range(len(DAYS)):
        for hi in range(len(HOURS)):
            v = min(1, live[di, hi]); ax.text(hi, di, f"{v:.0%}", ha="center", va="center", fontsize=7,
                                             color="white" if v > 0.6 else "black")
fig.suptitle("Year 4 forecast: share of each hour Room A is expected to be booked (Mon-Fri, 8 AM-5 PM)")
fig.colorbar(im, ax=axes, fraction=0.015); plt.savefig(IMG / "hourly_heatmap_forecast.png", dpi=150, bbox_inches="tight"); plt.close()

profile = {q: sum(w * grids[(y, q)] for y, w in LIVE_WEIGHTS.items()).clip(max=1).mean(axis=0) for q in QUARTERS}
plt.figure(figsize=(8, 4))
for q, v in profile.items():
    plt.plot(HOUR_LABELS, v, marker="o", label=q)
plt.ylim(0, 1); plt.gca().yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
plt.xlabel("Hour starting"); plt.ylabel("Share of hour booked"); plt.title("Year 4 forecast: average use by hour of day")
plt.legend(frameon=False); plt.tight_layout(); plt.savefig(IMG / "hourly_profile.png", dpi=150); plt.close()
print(f"\nCharts saved to {IMG}")
