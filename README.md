# Room Utilization Forecast: Hourly Capacity Model for a Shared Department Room

A capacity model that forecasts how a 36-seat department meeting room is used, hour by hour from 8 AM to 5 PM on weekdays, using three years of booking history. It was built to answer a practical question: **if the university's central scheduling office (the Registrar) wants to share this room, which hours can we offer without displacing current users, and what would combined use look like?**

All data is anonymized. Lab, course, and person names, the room number, the building, and calendar dates have been removed.

![Hourly forecast heatmap](images/hourly_heatmap_forecast.png)

## The problem

The Registrar's Office proposed using the room for scheduled classes. The department needed evidence of how much the room is actually used, and when, to decide what time it could offer and to support a counter proposal.

## Data

| File | What it contains |
|---|---|
| `data/weekly_bookings.csv` | Number of bookings in every academic week for 3 years (42 weeks per year, aligned by instructional week) |
| `data/booking_log_sample_weeks.csv` | Start and end times of every booking in one full mid-quarter week per quarter per year, plus 3 weeks of the current year |
| `data/sample_week_booking_lengths.csv` | Average booking length per quarter and year, from those sample weeks |

Weeks are aligned by **academic week**, not calendar date, so quarter start dates that shift each year don't distort the comparison.

## Method

1. **Weekly volume.** Count bookings for every academic week over three years.
2. **Weekly hours.** Multiply each week's bookings by that quarter's average booking length.
3. **Hourly usage.** Convert each sample week's bookings into the share of each hour (8–9 AM through 4–5 PM) that was booked, per weekday. Overlapping bookings are capped at 100% of the hour.
4. **Forecast.** Take a weighted average of the three years (20% / 30% / 50%, most recent highest), with an optional growth rate and event adjustments.
5. **Scheduling scenario.** Score each standard class meeting pattern (MWF 50 min, TTh 80 min, and so on) against the forecast by expected use (time-weighted) and worst-case hour. Label each pattern Open, Check first, or Conflict, then build a non-overlapping Registrar scenario and the resulting combined-use heatmap.
6. **Accuracy tracking.** Compare the current year's actual weeks with the forecast, slot by slot.

## Backtest

To test the method honestly, I forecast **Year 3 using only Years 1 and 2** (weighted 40/60), then compared the result with what actually happened. As a benchmark, I also scored a naive "same as last year" forecast.

| Metric | Model | Naive (last year) |
|---|---|---|
| Weekly bookings: WAPE | **21.4%** | 27.3% |
| Weekly hours: WAPE | **21.1%** | 26.5% |
| Annual total bookings: bias | **+14.1%** | +16.4% |
| Annual total hours: bias | **+9.6%** | +13.8% |
| Hourly: mean absolute error | **30.6 pts** | 31.4 pts |
| Hourly: busy/open called correctly (180 weekday hour slots) | **66.1%** | 64.4% |

WAPE is the total absolute error divided by total actual volume. Run `python analysis/backtest.py` to reproduce these numbers.

![Backtest](images/backtest_weekly.png)

**What the backtest shows**

- The model beats the naive forecast on every measure, and on weekly volume it cuts error by about a fifth.
- **Fall and Spring forecast well** (−1.5% and +6.1% on quarterly totals). **Winter and Summer were over-forecast** (+21% and +88%). Year 3 lost several recurring bookings in those quarters, including a weekly course and a summer program. Normal year-to-year variation can't predict a change like that, which is why the model has an Event Adjustments input for known changes.
- **Hour-level prediction is the hard part.** The model calls busy versus open correctly about two-thirds of the time, only slightly better than naive. A room like this is driven by a handful of recurring meetings that move between years. The practical lesson is to treat the hourly forecast as a likelihood map, confirm specific slots with the department, and refresh it each quarter as bookings are made.

## Key findings (Year 4 forecast)

- The room is used about **44% of available weekday hours** during the academic year and about 25% in summer.
- **12–1 PM is the peak**, booked 81–86% of the time in fall and winter. **3–5 PM is a second peak** at about 60–70%.
- **8–9 AM is almost always free**, and Tue/Thu mornings and 2–3 PM are lightly used.
- The best-fitting Registrar patterns are **TTh 9:00–10:20, TTh 10:30–11:50, MWF 8:30–9:20, and MW 10:30–11:50**. Adding them would put the room at about **67–75% combined use**, or roughly 10–15 Registrar hours a week.

![Hourly profile](images/hourly_profile.png)

## Workbook guide

`model/Room_A_Hourly_Usage_Forecast.xlsx` is fully formula-driven. Blue cells are inputs; everything else recalculates.

| Tab | Purpose |
|---|---|
| Registrar Projection | Weekly and quarterly Registrar hours and combined utilization |
| Backtest | Year 3 forecast vs. actual, model vs. naive, weekly and hourly |
| Summary | Hours, utilization, busiest and quietest hours per quarter |
| Assumptions | Growth, year weights, thresholds, weeks per quarter |
| Registrar Patterns | Each standard meeting pattern scored Open / Check first / Conflict, with 1/0 assignment |
| Combined Use | Department + Registrar heatmaps; cells over 100% flag possible clashes |
| Finals Exam Blocks | Three-hour exam blocks vs. finals-week department use |
| Forecast | Hourly forecast heatmaps by quarter |
| Current Fall Actual | This year's actual hourly use vs. forecast |
| Hourly Usage, Weekly History, Booking Log | Source data and intermediate calculations |

## Limitations

- Hourly patterns come from **one sample week per quarter per year**. That captures recurring weekly meetings but not one-off events.
- Historical hours are estimates (bookings × sampled average length).
- Standard meeting patterns and exam block times follow a typical university grid and are editable.
- This is a "how much fits" projection, not a forecast of actual Registrar demand.

## Tools

Excel (formula-driven model, conditional-format heatmaps), Python (pandas, matplotlib, openpyxl) for data preparation, backtesting, and charts.

## Repo structure

```
├── README.md
├── model/Room_A_Hourly_Usage_Forecast.xlsx
├── data/                  anonymized inputs (CSV)
├── analysis/backtest.py   reproduces backtest metrics and charts
└── images/                charts used in this README
```
