from flask import Blueprint, jsonify, session, request
import asyncio
import json
from src.services.mcp_client import get_login_url, is_session_active
from src.agent_orchestrator import AgentDataOrchestrator
orchestrator = AgentDataOrchestrator()
from src.database.json_mongo import (
    fetch_networth, fetch_assets, fetch_credit, fetch_monthly_trend,
    fetch_mf_transactions, fetch_bank_transactions,
    fetch_epf_details, fetch_stock_transactions
)


mcp_bp = Blueprint("mcp", __name__, url_prefix="/api/mcp")

@mcp_bp.route("/login", methods=["GET"])
def login():
    login_url = asyncio.run(get_login_url())
    return jsonify({"login_url": login_url})


# POST /login route for OTP-based login and tool fetching
@mcp_bp.route("/login", methods=["POST"])
def perform_login():
    phone = request.form.get("phoneNumber")
    otp = request.form.get("otp")
    session_id = "myve"

    if not phone or not otp:
        return jsonify({"error": "Missing phone number or OTP"}), 400

    # Store phone number in session and establish session
    session["mobile_number"] = phone
    session["myve"] = {
        "authenticated": True,
        "tools": ["networth", "assets", "credit", "monthly_trend"],
        "sessionId": session_id
    }

    # Call fetch logic after login
    try:
        print("== MCP Backend Test Fetch ==")
        networth = asyncio.run(fetch_networth(phone))
        assets = asyncio.run(fetch_assets(phone))
        credit = asyncio.run(fetch_credit(phone))
        trend = asyncio.run(fetch_monthly_trend(phone))

        print("✅ Networth:", json.dumps(networth, indent=2))
        print("✅ Assets:", json.dumps(assets, indent=2))
        print("✅ Credit:", json.dumps(credit, indent=2))
        print("✅ Monthly Trend:", json.dumps(trend, indent=2))

        return jsonify({"message": "Login successful", "tools": session[session_id]["tools"]})
    except Exception as e:
        print("❌ Error during test fetch:", e)
        return jsonify({"error": str(e)}), 500

@mcp_bp.route("/status", methods=["GET"])
def status():
    active = asyncio.run(is_session_active())
    return jsonify({"authenticated": active})

@mcp_bp.route("/connect", methods=["GET"])
def connect():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile number not in session"}), 400

    session["myve"] = {
        "authenticated": True,
        "tools": ["networth", "assets", "credit", "monthly_trend"],
        "sessionId": "myve"
    }

    try:
        print("== MCP Backend Test Fetch ==")
        networth = asyncio.run(fetch_networth(mobile))
        assets = asyncio.run(fetch_assets(mobile))
        credit = asyncio.run(fetch_credit(mobile))
        trend = asyncio.run(fetch_monthly_trend(mobile))

        print("✅ Networth:", json.dumps(networth, indent=2))
        print("✅ Assets:", json.dumps(assets, indent=2))
        print("✅ Credit:", json.dumps(credit, indent=2))
        print("✅ Monthly Trend:", json.dumps(trend, indent=2))
    except Exception as e:
        print("❌ Error during test fetch:", e)

    return jsonify({"tools": session["myve"]["tools"]})



@mcp_bp.route("/assets", methods=["GET"])
def assets():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400
    refresh = request.args.get("refresh", "false").lower() == "true"
    doc = asyncio.run(fetch_assets(mobile, force_refresh=refresh))
    if not doc:
        return jsonify([])
    data = doc if isinstance(doc, dict) else {}
    return jsonify(data.get("assets", []))

@mcp_bp.route("/credit", methods=["GET"])
def credit():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400
    refresh = request.args.get("refresh", "false").lower() == "true"
    doc = asyncio.run(fetch_credit(mobile, force_refresh=refresh))
    if not doc:
        return jsonify({})
    data = doc if isinstance(doc, dict) else {}
    if "creditReportData" not in data:
        data["creditReportData"] = {}
    return jsonify(data)

@mcp_bp.route("/monthly_trend", methods=["GET"])
def monthly_trend():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400
    refresh = request.args.get("refresh", "false").lower() == "true"
    data = asyncio.run(fetch_monthly_trend(mobile, force_refresh=refresh))
    if not data:
        return jsonify({})
    return jsonify(data)



# Route to get session information
@mcp_bp.route("/sessions", methods=["GET"])
def sessions():
    try:
        session_data = session.get("myve", {})
        return jsonify({
            "myve": bool(session_data.get("authenticated", False)),
            "tools": session_data.get("tools", [])
        })
    except Exception as e:
        print("❌ Error in /sessions route:", e)
        return jsonify({"myve": False, "error": str(e)}), 500

# Route to get current profile (mobile number)
@mcp_bp.route("/profile", methods=["GET"])
def profile():
    try:
        mobile = session.get("mobile_number")
        return jsonify({"mobile": mobile or ""})
    except Exception as e:
        print("❌ Error in /profile route:", e)
        return jsonify({"error": str(e)}), 500


# Additional routes for mf_transactions, bank_transactions, epf, stocks
@mcp_bp.route("/mf_transactions", methods=["GET"])
def mf_transactions():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400
    refresh = request.args.get("refresh", "false").lower() == "true"
    doc = asyncio.run(fetch_mf_transactions(mobile, force_refresh=refresh))
    if not doc:
        return jsonify([])
    data = doc if isinstance(doc, dict) else {}
    transactions = data.get("transactions")
    if not transactions:
        transactions = data.get("mfAnalytics", [])
        if not isinstance(transactions, list):
            transactions = []
    return jsonify(transactions)

@mcp_bp.route("/bank_transactions", methods=["GET"])
def bank_transactions():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400
    refresh = request.args.get("refresh", "false").lower() == "true"
    doc = asyncio.run(fetch_bank_transactions(mobile, force_refresh=refresh))
    if not doc:
        return jsonify([])
    data = doc if isinstance(doc, dict) else {}
    transactions = data.get("transactions")
    if not transactions:
        transactions = data.get("flattenedAccounts", [])
    if not isinstance(transactions, list):
        transactions = []
    return jsonify(transactions)

@mcp_bp.route("/epf", methods=["GET"])
def epf():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400
    refresh = request.args.get("refresh", "false").lower() == "true"
    data = asyncio.run(fetch_epf_details(mobile, force_refresh=refresh))
    if not data:
        return jsonify({})
    return jsonify(data)


@mcp_bp.route("/stocks", methods=["GET"])
def stocks():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400
    refresh = request.args.get("refresh", "false").lower() == "true"
    doc = asyncio.run(fetch_stock_transactions(mobile, force_refresh=refresh))
    if not doc:
        return jsonify([])
    data = doc if isinstance(doc, dict) else {}
    transactions = data.get("stockTransactions")
    if not isinstance(transactions, list):
        transactions = []
    return jsonify(transactions)


# Route to return summary of data presence
@mcp_bp.route("/summary", methods=["GET"])
def summary():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400

    result = {}

    try:
        credit_data = asyncio.run(fetch_credit(mobile))
        result["hasCreditReport"] = isinstance(credit_data, list) and len(credit_data) > 0

        stock_data = asyncio.run(fetch_stock_transactions(mobile))
        result["hasStocks"] = isinstance(stock_data, list) and len(stock_data) > 0

        epf_data = asyncio.run(fetch_epf_details(mobile))
        result["hasEpf"] = bool(epf_data and epf_data.get("uanAccounts"))
    except Exception as e:
        print("❌ Error in /summary route:", e)

    return jsonify(result)


# Route to handle agent orchestrator query
@mcp_bp.route("/query", methods=["POST"])
def handle_query():
    body = request.json or {}
    query = body.get("query", "")
    mobile = body.get("mobile")

    if not query:
        return jsonify({"error": "Missing query"}), 400
    if not mobile:
        return jsonify({"error": "Missing mobile number"}), 400

    try:
        result = asyncio.run(agent_orchestrator(query, mobile))
        return jsonify(result)
    except Exception as e:
        print("❌ Error in /query route:", e)
        return jsonify({"error": str(e)}), 500

@mcp_bp.route("/api/query", methods=["GET"])
def query_router():
    mobile = request.args.get("mobile")
    query = request.args.get("query")
    from src.services.gemini_handler import detect_financial_intent
    from src.agents.agent_orchestrator import route_query_intent

    if not mobile or not query:
        return jsonify({"error": "Missing mobile or query"}), 400

    try:
        intent = detect_financial_intent(query)
        result = asyncio.run(route_query_intent(intent, mobile))
        return jsonify(result)
    except Exception as e:
        print("❌ Error in /api/query route:", e)
        return jsonify({"error": str(e)}), 500
    
    
@mcp_bp.route("/networth", methods=["GET"])
def networth():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not set"}), 400

    try:
        refresh = request.args.get("refresh", "false").lower() == "true"

        networth_data = asyncio.run(fetch_networth(mobile, force_refresh=refresh))
        credit_data = asyncio.run(fetch_credit(mobile, force_refresh=refresh))
        assets_data = asyncio.run(fetch_assets(mobile, force_refresh=refresh))
        trend_data = asyncio.run(fetch_monthly_trend(mobile, force_refresh=refresh))
        epf_data = asyncio.run(fetch_epf_details(mobile, force_refresh=refresh))
        mf_data = asyncio.run(fetch_mf_transactions(mobile, force_refresh=refresh))
        bank_data = asyncio.run(fetch_bank_transactions(mobile, force_refresh=refresh))
        stock_data = asyncio.run(fetch_stock_transactions(mobile, force_refresh=refresh))

        merged = {
            "netWorth": {},
            "assets": [],
            "accounts": {},
            "creditReport": {},
            "monthlyTrend": [],
            "epf": epf_data if isinstance(epf_data, dict) else {},
            "mfTransactions": [],
            "bankTransactions": [],
            "stocks": []
        }

        if isinstance(networth_data, dict):
            merged["netWorth"] = networth_data.get("netWorth", {}) if isinstance(networth_data.get("netWorth"), dict) else {}
            merged["accounts"] = networth_data.get("accounts", {}) if isinstance(networth_data.get("accounts"), dict) else {}

        if isinstance(assets_data, dict):
            merged["assets"] = assets_data.get("assets", []) if isinstance(assets_data.get("assets"), list) else []

        # Patch: Properly extract creditReportData from creditReports list if present
        if isinstance(credit_data, dict) and "creditReports" in credit_data:
            reports = credit_data.get("creditReports", [])
            if isinstance(reports, list) and len(reports) > 0:
                merged["creditReport"] = reports[0].get("creditReportData", {})
            else:
                merged["creditReport"] = {}

        if isinstance(trend_data, dict):
            merged["monthlyTrend"] = trend_data.get("trend", []) if isinstance(trend_data.get("trend", []), list) else []
        elif isinstance(trend_data, list):
            merged["monthlyTrend"] = trend_data

        if isinstance(mf_data, dict):
            mf_txns = mf_data.get("transactions")
            if not isinstance(mf_txns, list):
                mf_txns = mf_data.get("mfAnalytics", [])
            if not isinstance(mf_txns, list):
                mf_txns = []
            merged["mfTransactions"] = mf_txns
        elif isinstance(mf_data, list):
            merged["mfTransactions"] = mf_data

        if isinstance(bank_data, dict):
            bank_txns = bank_data.get("transactions")
            if not isinstance(bank_txns, list):
                bank_txns = bank_data.get("flattenedAccounts", [])
            if not isinstance(bank_txns, list):
                bank_txns = []
            merged["bankTransactions"] = bank_txns
        elif isinstance(bank_data, list):
            merged["bankTransactions"] = bank_data

        if isinstance(stock_data, dict):
            merged["stocks"] = stock_data.get("stockTransactions", []) if isinstance(stock_data.get("stockTransactions"), list) else []
        elif isinstance(stock_data, list):
            merged["stocks"] = stock_data

        return jsonify({"data": merged})
    except Exception as e:
        print("❌ Error in /networth:", e)
        return jsonify({"error": str(e)}), 500


# Route for full orchestrator snapshot
@mcp_bp.route("/full_snapshot", methods=["GET"])
def full_snapshot():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile number not in session"}), 400

    try:
        snapshot = orchestrator.get_user_data(mobile)
        return jsonify({"data": snapshot})
    except Exception as e:
        print("❌ Error in /full_snapshot route:", e)
        return jsonify({"error": str(e)}), 500