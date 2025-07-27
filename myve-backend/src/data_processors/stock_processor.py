import pandas as pd
from datetime import datetime
from collections import defaultdict
from loguru import logger

class StockAnalyzer:
    @staticmethod
    def analyze(user_id, stock_data):
        
        summary = {
            "total_invested": 0.0,
            "total_realized": 0.0,
            "current_holdings": defaultdict(lambda: {"quantity": 0, "value": 0.0}),
            "capital_gains": 0.0,
            "monthly_trend": defaultdict(float)
        }

        for stock in stock_data:
            isin = stock.get("isin", "UNKNOWN")
            txns = stock.get("txns", [])
            if not isinstance(txns, list):
                logger.warning(f"Invalid transactions list for stock ISIN {stock.get('isin')}")
                continue
            for txn in txns:
                if not isinstance(txn, list) or len(txn) < 3:
                    logger.warning(f"Skipping invalid or incomplete transaction: {txn}")
                    continue  # skip incomplete records

                txn_type, txn_date, quantity = txn[:3]
                nav_value = txn[3] if len(txn) > 3 else None
                try:
                    date_obj = datetime.strptime(txn_date, "%Y-%m-%d")
                except Exception as e:
                    logger.warning(f"Invalid date '{txn_date}' in transaction: {txn} - {e}")
                    continue
                month_key = date_obj.strftime("%Y-%m")

                if txn_type == 1:  # BUY
                    if nav_value is not None:
                        amount = quantity * nav_value
                        summary["total_invested"] += amount
                        summary["current_holdings"][isin]["quantity"] += quantity
                        summary["current_holdings"][isin]["value"] += amount
                        summary["monthly_trend"][month_key] += amount
                elif txn_type == 2:  # SELL
                    if nav_value is not None:
                        proceeds = quantity * nav_value
                        summary["total_realized"] += proceeds
                        summary["current_holdings"][isin]["quantity"] -= quantity
                        summary["current_holdings"][isin]["value"] -= quantity * nav_value
                        summary["capital_gains"] += proceeds  # simplified gain calculation
                        summary["monthly_trend"][month_key] += proceeds
                elif txn_type == 3:  # BONUS
                    summary["current_holdings"][isin]["quantity"] += quantity
                elif txn_type == 4:  # SPLIT
                    summary["current_holdings"][isin]["quantity"] += quantity

        return {"summary": summary}