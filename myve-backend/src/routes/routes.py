


from flask import Blueprint, jsonify
from src.services.mcp_client import (
    fetch_networth, fetch_credit, fetch_epf_details,
    fetch_mf_transactions, fetch_bank_transactions, fetch_stock_transactions
)

routes = Blueprint('routes', __name__)

from flask import session
import asyncio

@routes.route("/api/user/financial-profile", methods=["GET"])
def get_financial_profile():
    mobile = session.get("mobile_number")
    if not mobile:
        return jsonify({"error": "Mobile not in session"}), 400

    profile = {
        "netWorth": asyncio.run(fetch_networth(mobile)),
        "creditReport": asyncio.run(fetch_credit(mobile)),
        "epfDetails": asyncio.run(fetch_epf_details(mobile)),
        "mfTransactions": asyncio.run(fetch_mf_transactions(mobile)),
        "bankTransactions": asyncio.run(fetch_bank_transactions(mobile)),
        "stockHoldings": asyncio.run(fetch_stock_transactions(mobile)),
    }
    return jsonify(profile)