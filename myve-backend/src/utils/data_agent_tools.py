
import pandas as pd
from datetime import datetime
from collections import OrderedDict

def build_graph_data(context):
    bank_txns = context.get("bank_txns", [])
    mf_txns = context.get("mf_txns", [])
    credit_raw = context.get("credit", {})
    if isinstance(credit_raw, dict):
        credit_data = credit_raw.get("accounts", [])
    else:
        credit_data = credit_raw  # assume list fallback
    assets = context.get("assets", [])
    networth_history = context.get("networth", {}).get("history", [])

    # PIE: Category-wise total (bank + mf)
    # Shows distribution of spending across categories from bank and mutual fund transactions
    category_totals = {}
    for txn in bank_txns + mf_txns:
        category = txn.get("category", "Other")
        amount = abs(float(txn.get("amount", 0)))
        category_totals[category] = category_totals.get(category, 0) + amount

    pie_data = {
        "type": "pie",
        "labels": list(category_totals.keys()),
        "data": list(category_totals.values()),
        "title": "Spending Distribution by Category"
    }

    from src.services.gemini_service import call_gemini

    pie_insight = call_gemini(
        "Summarize the user's spending distribution across categories from this data:\n"
        + str(pie_data["data"])
    )
    pie_data["insight"] = pie_insight

    # LINE: Monthly spending trend (Bank only)
    # Tracks monthly spending amounts to identify trends over time
    monthly_trend = {}
    for txn in bank_txns:
        date_str = txn.get("date")
        amount = abs(float(txn.get("amount", 0)))
        if date_str:
            try:
                month = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
                monthly_trend[month] = monthly_trend.get(month, 0) + amount
            except ValueError:
                continue

    monthly_trend = OrderedDict(sorted(monthly_trend.items()))
    trend_data = list(monthly_trend.values())
    sorted_months = list(monthly_trend.keys())

    line_data = {
        "type": "line",
        "labels": sorted_months,
        "data": trend_data,
        "title": "Monthly Spending Trend"
    }

    spending_insight = call_gemini(
        "Summarize the user's monthly spending pattern from this data:\n"
        + str(line_data["data"])
    )
    line_data["insight"] = spending_insight

    # Category-wise spend percent change vs last month
    from collections import defaultdict
    monthly_category_spend = defaultdict(lambda: defaultdict(float))
    for txn in bank_txns:
        date_str = txn.get("date")
        amount = abs(float(txn.get("amount", 0)))
        category = txn.get("category", "Other")
        if date_str:
            try:
                month = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
                monthly_category_spend[month][category] += amount
            except ValueError:
                continue

    sorted_cat_months = sorted(monthly_category_spend.keys())
    if len(sorted_cat_months) >= 2:
        last_month = sorted_cat_months[-1]
        prev_month = sorted_cat_months[-2]
        category_changes = []
        for cat in monthly_category_spend[last_month]:
            last_val = monthly_category_spend[last_month].get(cat, 0)
            prev_val = monthly_category_spend[prev_month].get(cat, 0)
            if prev_val > 0:
                change_pct = ((last_val - prev_val) / prev_val) * 100
                category_changes.append({
                    "category": cat,
                    "change_pct": round(change_pct, 2)
                })
    else:
        category_changes = []

    # Smart flags and recommendations
    insights = []
    for change in category_changes:
        if change["change_pct"] > 30:
            insights.append({
                "label": "Spending Spike",
                "value": f"{change['category']} up {change['change_pct']}%",
                "category": change["category"],
                "ai": True
            })
        elif change["change_pct"] < -20:
            insights.append({
                "label": "Reduced Spending",
                "value": f"{change['category']} down {abs(change['change_pct'])}%",
                "category": change["category"],
                "ai": True
            })

    # Sample recommendation format
    recommendations = [
        f"Consider reducing expenses in {c['category']}"
        for c in category_changes if c["change_pct"] > 30
    ]

    # BAR: Monthly credit usage
    # Shows credit balances over months from credit account histories
    credit_trend = {}
    for acct in credit_data:
        history = acct.get("history", [])
        for h in history:
            try:
                month = h.get("month", "unknown")
                balance = float(h.get("balance", 0))
                credit_trend[month] = credit_trend.get(month, 0) + balance
            except:
                continue

    credit_trend = OrderedDict(sorted(credit_trend.items()))
    credit_bar = {
        "type": "bar",
        "labels": list(credit_trend.keys()),
        "data": list(credit_trend.values()),
        "title": "Credit Usage Trend"
    }

    # DOUGHNUT: Asset distribution
    # Visualizes allocation of assets by type
    asset_totals = {}
    for asset in assets:
        label = asset.get("type", "Other")
        amount = float(asset.get("amount", 0))
        asset_totals[label] = asset_totals.get(label, 0) + amount

    doughnut_data = {
        "type": "doughnut",
        "labels": list(asset_totals.keys()),
        "data": list(asset_totals.values()),
        "title": "Asset Allocation"
    }

    # LINE: Net worth trend
    # Plots net worth changes over time
    networth_trend = {}
    for entry in networth_history:
        date = entry.get("date")
        amount = float(entry.get("amount", 0))
        if date:
            try:
                month = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m")
                networth_trend[month] = amount
            except:
                continue

    networth_trend = OrderedDict(sorted(networth_trend.items()))
    networth_line = {
        "type": "line",
        "labels": list(networth_trend.keys()),
        "data": list(networth_trend.values()),
        "title": "Net Worth Over Time"
    }

    # Placeholder for future interactive filtering and reactive summaries
    # e.g., filters = context.get("filters", {})

    return {
        "expense_pie": pie_data,
        "spending_line": line_data,
        "credit_bar": credit_bar,
        "asset_doughnut": doughnut_data,
        "networth_line": networth_line,
        "category_change": category_changes,
        "smart_insights": insights,
        "recommendations": recommendations
    }
def get_timeline_data(user_id):
    from src.services.mcp_client import fetch_bank_transactions
    from datetime import datetime
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        bank_txns = loop.run_until_complete(fetch_bank_transactions(user_id))
    finally:
        loop.close()

    # Normalize txns from raw schema
    flattened = []
    for entry in bank_txns:
        for txn in entry.get("txns", []):
            try:
                amt = float(txn[0])
                narration = txn[1]
                date = txn[2]
                ttype = txn[3]
                txn_type = "CREDIT" if ttype == 2 else "DEBIT"
                flattened.append({
                    "amount": amt,
                    "narration": narration,
                    "date": date,
                    "type": txn_type
                })
            except Exception as e:
                continue
    bank_txns = flattened

    timeline = {}
    for txn in bank_txns:
        try:
            date = txn.get("date")
            amt = float(txn.get("amount", 0))
            label = txn.get("category", txn.get("narration", "Txn"))
            if date:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                date_key = date_obj.strftime("%Y-%m-%d")
                if date_key not in timeline:
                    timeline[date_key] = []
                timeline[date_key].append({
                    "amount": amt,
                    "label": label
                })
        except:
            continue

    # Format into sorted list
    sorted_timeline = sorted(timeline.items(), key=lambda x: x[0])
    return [{"date": d, "txns": txns} for d, txns in sorted_timeline]


# AI-powered insight for a specific timeline date
def generate_insight_from_timeline_point(user_id, date_clicked):
    from src.services.mcp_client import fetch_bank_transactions
    from src.services.gemini_service import call_gemini
    from datetime import datetime
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        bank_txns = loop.run_until_complete(fetch_bank_transactions(user_id))
    finally:
        loop.close()

    # Flatten and filter transactions for the selected date
    flattened = []
    for entry in bank_txns:
        for txn in entry.get("txns", []):
            try:
                date = txn[2]
                if date == date_clicked:
                    amt = float(txn[0])
                    narration = txn[1]
                    ttype = txn[3]
                    txn_type = "CREDIT" if ttype == 2 else "DEBIT"
                    flattened.append({
                        "amount": amt,
                        "narration": narration,
                        "type": txn_type
                    })
            except:
                continue

    if not flattened:
        return {"insight": f"No transactions found for {date_clicked}"}

    prompt = (
        f"Given the following transactions on {date_clicked}, summarize spending patterns, highlight any unusual activity, "
        f"and offer relevant suggestions:\n\n"
        f"{flattened}"
    )

    ai_response = call_gemini(prompt)
    return {"insight": ai_response}