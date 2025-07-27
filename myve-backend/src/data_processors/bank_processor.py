import pandas as pd
from collections import defaultdict
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger(__name__)

class BankTransactionAnalyzer:
    def __init__(self, user_id: str, bank_data: dict):
        self.user_id = user_id
        self.bank_data = bank_data
        self.account_summary = {}

    def process(self):
        try:
            logger.info(f"[BankProcessor] Processing bank data for user: {self.user_id}")
            txn_records = []
            for account in self.bank_data.get("bankTransactions", []):
                bank_name = account.get("bank", "Unknown Bank")
                txns = account.get("txns", [])
                for txn in txns:
                    txn_records.append({
                        "bank": bank_name,
                        "amount": float(txn[0]) if txn[0] else 0.0,
                        "narration": txn[1] if len(txn) > 1 else "",
                        "date": datetime.strptime(txn[2], "%Y-%m-%d") if len(txn) > 2 and txn[2] else datetime.now(),
                        "type": int(txn[3]) if len(txn) > 3 and txn[3] else 8,
                        "mode": txn[4] if len(txn) > 4 else "UNKNOWN",
                        "balance": float(txn[5]) if len(txn) > 5 and txn[5] else 0.0
                    })

            df = pd.DataFrame(txn_records)
            if df.empty:
                return {"summary": {}, "monthlyTrend": []}

            num_accounts = len(self.bank_data.get("bankTransactions", []))
            total_credits = df[df["type"] == 1]["amount"].sum() if "amount" in df.columns else 0.0
            total_debits = df[df["type"] == 2]["amount"].sum() if "amount" in df.columns else 0.0
            avg_balance = df["balance"].mean() if "balance" in df.columns else 0.0

            monthly = (
                df.groupby(df["date"].dt.to_period("M")).agg({
                    "amount": ["sum"] if "amount" in df.columns else [],
                    "balance": ["mean"] if "balance" in df.columns else []
                }).reset_index()
                if not df.empty and "date" in df.columns
                else pd.DataFrame(columns=["month", "totalAmount", "avgBalance"])
            )
            if not monthly.empty:
                monthly.columns = ["month", "totalAmount", "avgBalance"][:len(monthly.columns)]
                monthly["month"] = monthly["month"].astype(str)

            erratic_withdrawals = (
                df[(df["type"] == 2) & (df["amount"] > df["amount"].mean() + 2 * df["amount"].std())]
                if "amount" in df.columns else pd.DataFrame()
            )

            self.account_summary = {
                "userId": self.user_id,
                "numAccounts": num_accounts,
                "totalCredits": total_credits,
                "totalDebits": total_debits,
                "averageBalance": avg_balance,
                "erraticWithdrawals": erratic_withdrawals.to_dict(orient="records"),
                "monthlyTrend": monthly.to_dict(orient="records")
            }

            logger.info(f"[BankProcessor] Finished processing for user: {self.user_id}")
            return {"summary": self.account_summary}

        except Exception as e:
            logger.error(f"[BankProcessor] Failed to process bank data: {e}")
            return {"summary": {}, "monthlyTrend": []}