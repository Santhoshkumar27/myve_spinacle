import json
import os

TEST_DATA_DIR = "/Users/santhoshkumar/Downloads/fi-mcp-dev-master/test_data_dir"
SESSION_ID = "myve"

def read_mock_json(filename, mobile_number):
    file_path = os.path.join(TEST_DATA_DIR, mobile_number, filename)
    with open(file_path, "r") as file:
        return json.load(file)

async def get_login_url():
    return f"http://localhost:8080/mockWebPage?sessionId={SESSION_ID}"

async def is_session_active():
    return True

async def get_user_tools():
    return {
        "tools": ["networth", "assets", "credit", "monthly_trend"]
    }

async def fetch_networth(mobile_number):
    raw_data = read_mock_json("fetch_net_worth.json", mobile_number)
    return {
        "netWorth": raw_data.get("netWorthResponse", {}).get("totalNetWorthValue", {}) or {},
        "assets": raw_data.get("netWorthResponse", {}).get("assetValues", []) or [],
        "liabilities": raw_data.get("netWorthResponse", {}).get("liabilityValues", []) or [],
        "mfAnalytics": raw_data.get("mfSchemeAnalytics", {}).get("schemeAnalytics", []) or [],
        "accounts": raw_data.get("accountDetailsBulkResponse", {}).get("accountDetailsMap", {}) or {},
        "epf": {
            k: v["epfSummary"]
            for k, v in (raw_data.get("accountDetailsBulkResponse", {}).get("accountDetailsMap", {}) or {}).items()
            if "epfSummary" in v
        }
    }

async def fetch_credit(mobile_number):
    raw_data = read_mock_json("fetch_credit_report.json", mobile_number)
    return raw_data.get("creditReports", []) or []

async def fetch_assets(mobile_number):
    networth_data = await fetch_networth(mobile_number)
    return networth_data.get("assets", [])

import datetime
from collections import defaultdict

def month_key(date_str):
    dt = datetime.datetime.fromisoformat(date_str.replace("Z", ""))
    return dt.strftime("%Y-%m")

async def fetch_monthly_trend(mobile_number):
    raw_data = read_mock_json("fetch_net_worth.json", mobile_number)
    accounts = raw_data.get("accountDetailsBulkResponse", {}).get("accountDetailsMap", {})

    trend_map = defaultdict(int)

    # Include deposit accounts
    for acc_id, acc_data in accounts.items():
        summary = acc_data.get("depositSummary")
        if summary and "balanceDate" in summary and "currentBalance" in summary:
            date = summary["balanceDate"]
            amount = int(summary["currentBalance"].get("units", 0))
            month = month_key(date)
            trend_map[month] += amount

    # Include equity, ETF, REIT, INVIT accounts if present
    for acc_id, acc_data in accounts.items():
        for field in ["equitySummary", "etfSummary", "reitSummary", "invitSummary"]:
            summary = acc_data.get(field)
            if summary and "currentValue" in summary:
                # Use current date for simplification
                now = datetime.datetime.now()
                month = now.strftime("%Y-%m")
                amount = int(summary["currentValue"].get("units", 0))
                trend_map[month] += amount

    return [{"month": k, "value": v} for k, v in sorted(trend_map.items())]

async def test_fetch(mobile_number):
    print("== MCP Backend Test Fetch ==")
    try:
        networth = await fetch_networth(mobile_number)
        print("✅ Networth:", json.dumps(networth["netWorth"], indent=2))
        print("✅ Assets:", json.dumps(networth["assets"], indent=2))
        credit = await fetch_credit(mobile_number)
        print("✅ Credit:", json.dumps(credit, indent=2))
        trend = await fetch_monthly_trend(mobile_number)
        print("✅ Monthly Trend:", json.dumps(trend, indent=2))
    except Exception as e:
        print("❌ Error during test fetch:", e)

async def fetch_mf_transactions(mobile_number):
    raw_data = read_mock_json("fetch_mf_transactions.json", mobile_number)
    return raw_data.get("mfTransactions", []) or []

async def fetch_bank_transactions(mobile_number):
    raw_data = read_mock_json("fetch_bank_transactions.json", mobile_number)
    print(f"[DEBUG] Fetched bank transactions for {mobile_number}: {len(raw_data.get('bankTransactions', []))} items")
    return raw_data.get("bankTransactions", []) or []

async def fetch_epf_details(mobile_number):
    raw_data = read_mock_json("fetch_epf_details.json", mobile_number)
    return raw_data if raw_data else {}

async def fetch_stock_transactions(mobile_number):
    raw_data = read_mock_json("fetch_stock_transactions.json", mobile_number)
    return raw_data.get("stockTransactions", []) or []