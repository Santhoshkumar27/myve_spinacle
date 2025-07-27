"""
Mutual Fund Processor

Responsibilities:
- Track current holdings value
- Summarize investments by type (ELSS, equity, debt, etc.)
- Analyze returns over time (monthly)
- Track SIPs based on transaction patterns
"""

import json
from collections import defaultdict
from datetime import datetime

class MutualFundAnalyzer:
    def __init__(self, user_id, mf_data):
        self.user_id = user_id
        self.mf_data = mf_data

    def process(self):
        summary = {
            "userId": self.user_id,
            "totalValue": 0.0,
            "summaryByType": defaultdict(float),
            "monthlyReturns": defaultdict(float),
            "sipCount": 0
        }

        for fund in self.mf_data:
            scheme = fund.get("schemeName", "")
            txns = fund.get("txns", [])
            if not txns:
                continue  # Skip if no transactions

            total_units = 0
            latest_nav = 0
            folio = fund.get("folioId", "")

            for txn in txns:
                if not isinstance(txn, list) or len(txn) < 5:
                    continue  # Skip invalid entries

                order_type, txn_date, nav, units, amount = txn
                if order_type == 1:  # BUY
                    total_units += units
                    if 2900 <= amount <= 5100:
                        summary["sipCount"] += 1
                elif order_type == 2:  # SELL
                    total_units -= units

                month_key = txn_date[:7]
                summary["monthlyReturns"][month_key] += amount

                txn_dt = datetime.strptime(txn_date, "%Y-%m-%d")
                if txn_dt > datetime.strptime("2000-01-01", "%Y-%m-%d"):
                    latest_nav = nav

            current_value = total_units * latest_nav
            summary["totalValue"] += current_value

            if "ELSS" in scheme.upper():
                summary["summaryByType"]["ELSS"] += current_value
            elif "DEBT" in scheme.upper():
                summary["summaryByType"]["Debt"] += current_value
            elif "BALANCED" in scheme.upper() or "HYBRID" in scheme.upper():
                summary["summaryByType"]["Hybrid"] += current_value
            elif "COMMODITIES" in scheme.upper():
                summary["summaryByType"]["Commodities"] += current_value
            elif "DIGITAL" in scheme.upper() or "THEME" in scheme.upper():
                summary["summaryByType"]["Thematic"] += current_value
            else:
                summary["summaryByType"]["Equity"] += current_value

        summary["summaryByType"] = dict(summary["summaryByType"])
        summary["monthlyReturns"] = dict(sorted(summary["monthlyReturns"].items()))
        return {"summary": summary}