from collections import defaultdict
from datetime import datetime
import math

# Simple category-specific saving ideas
category_tips = {
    "Groceries": "Plan weekly meals, buy generics, and avoid frequent small trips.",
    "Dining": "Batch-cook on weekends and set a 'dining out' cap per week.",
    "Transport": "Combine errands into one trip and compare fuel apps.",
    "Shopping": "Use a 24-hour rule for non-essentials; track return windows.",
    "Entertainment": "Rotate subscriptions monthly; look for student discounts.",
    "Rent": "Renegotiate at renewal, or find a roommate if reasonable.",
    "Utilities": "Set thermostat schedules and check for energy-efficient plans.",
    "Travel": "Book mid-week, and set far-in-advance fare alerts.",
    "Health": "Use in-network providers; buy HSA/FSA eligible essentials in bulk.",
    "Other": "Set a monthly 'misc' cap and move leftover funds to savings."
}

def _to_year_month(d):
    return f"{d.year:04d}-{d.month:02d}"

def _linear_fit_forecast(xs, ys):
    """
    Fit y = a*x + b using least squares and forecast next x.
    xs: [0, 1, 2, ...]
    ys: list of floats
    """
    n = len(xs)
    if n == 0:
        return 0.0
    mean_x = sum(xs)/n
    mean_y = sum(ys)/n
    num = sum((x-mean_x)*(y-mean_y) for x, y in zip(xs, ys))
    den = sum((x-mean_x)**2 for x in xs) or 1e-9
    a = num/den
    b = mean_y - a*mean_x
    next_x = xs[-1] + 1
    forecast = a*next_x + b
    return max(0.0, forecast)

def _zscore(value, arr):
    if not arr:
        return 0.0
    mean = sum(arr)/len(arr)
    var = sum((x-mean)**2 for x in arr)/len(arr) if len(arr) > 1 else 0.0
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (value - mean)/std

def generate_insights(expenses):
    """
    Input: list of Expense objects (with .date, .amount, .category)
    Output: dict with per-category analytics and global suggestions
    """
    if not expenses:
        return {"summary": {"total": 0.0, "months": 0, "top_category": None},
                "per_category": {},
                "suggestions": ["Add expenses to unlock insights."]}

    # Aggregate totals
    total = sum(e.amount for e in expenses)
    by_cat = defaultdict(list)  # list of (date, amount)
    by_month_cat = defaultdict(lambda: defaultdict(float))

    for e in expenses:
        by_cat[e.category].append((e.date, e.amount))
        ym = _to_year_month(e.date)
        by_month_cat[e.category][ym] += e.amount

    # Determine month ordering across all data
    all_months = set()
    for cat, mm in by_month_cat.items():
        all_months |= set(mm.keys())
    months_sorted = sorted(all_months)  # YYYY-MM lexicographic works

    # Per-category analytics
    per_category = {}
    top_category, top_total = None, 0.0

    for cat, mm in by_month_cat.items():
        totals_series = [mm.get(m, 0.0) for m in months_sorted]
        cat_total = sum(totals_series)
        if cat_total > top_total:
            top_total = cat_total
            top_category = cat

        # Trend-based forecast
        xs = list(range(len(months_sorted)))
        if len([v for v in totals_series if v > 0]) >= 3:
            forecast = _linear_fit_forecast(xs, totals_series)
        else:
            # Fallback: mean of available months
            nonzeros = [v for v in totals_series if v > 0]
            forecast = sum(nonzeros)/len(nonzeros) if nonzeros else 0.0

        # Last month anomaly z-score (relative to prior months)
        last_val = totals_series[-1] if totals_series else 0.0
        prior = totals_series[:-1] if len(totals_series) > 1 else []
        z_last = _zscore(last_val, prior) if prior else 0.0

        # Savings target: aim for 90% of forecast if last month exceeded forecast
        savings_target = max(0.0, round(0.9 * forecast, 2))
        rec = []
        if last_val > forecast * 1.1:
            rec.append(f"Last month in {cat} was higher than trend. Aim for ${savings_target:.2f} next month.")
        elif forecast > 0:
            rec.append(f"Stay on track in {cat}. Expected spend next month: ${forecast:.2f}.")
        if z_last >= 1.5:
            rec.append(f"Possible spike in {cat} last month (z≈{z_last:.1f}). Review big charges.")
        if cat in category_tips:
            rec.append(category_tips[cat])

        per_category[cat] = {
            "total": round(cat_total, 2),
            "last_month": round(last_val, 2),
            "forecast_next": round(forecast, 2),
            "suggested_cap": savings_target,
            "notes": rec
        }

    # Global suggestions
    suggestions = []
    # Identify top 2 categories by forecast for targeted budget
    top2 = sorted(per_category.items(), key=lambda kv: kv[1]["forecast_next"], reverse=True)[:2]
    for cat, data in top2:
        suggestions.append(f"Set a monthly soft cap for {cat} around ${data['suggested_cap']:.2f}.")

    # If spending trending up overall (compare last 3 months with prior 3)
    month_totals = defaultdict(float)
    for cat, mm in by_month_cat.items():
        for m, v in mm.items():
            month_totals[m] += v
    months_sorted_total = sorted(month_totals.keys())
    if len(months_sorted_total) >= 6:
        recent = months_sorted_total[-3:]
        earlier = months_sorted_total[-6:-3]
        r_avg = sum(month_totals[m] for m in recent)/3.0
        e_avg = sum(month_totals[m] for m in earlier)/3.0
        if r_avg > e_avg * 1.1:
            suggestions.append("Overall spending has risen ~10%+ in the last quarter vs the previous. Consider a temporary 5–10% cut across variable categories.")

    summary = {
        "total": round(total, 2),
        "months": len(months_sorted),
        "top_category": top_category
    }

    return {"summary": summary, "per_category": per_category, "suggestions": suggestions}
