import json
from statistics import mean
from loguru import logger

def process_credit_report(user_id: str, data: dict) -> dict:
    """
    Process credit report data to extract summary metrics.
    Returns a structured dictionary with credit analytics.
    """

    # Gracefully handle if data is a list instead of dict
    if isinstance(data, list):
        data = data[0] if data else {}
    
    try:
        if "creditReports" in data:
            credit_reports = data["creditReports"]
        else:
            credit_reports = [data]
        if not credit_reports or not isinstance(credit_reports[0], dict):
            raise ValueError("Missing or invalid 'creditReports' data")

        profile = credit_reports[0].get("creditReportData", {})
        credit_account = profile.get("creditAccount", {})
        summary = credit_account.get("creditAccountSummary", {})
        details = credit_account.get("creditAccountDetails", [])
        score_info = profile.get("score", {})
        bureau = score_info.get("bureau", "N/A")

        account_summary = summary.get("account", {})
        total_accounts = int(account_summary.get("creditAccountTotal", 0))
        active_accounts = int(account_summary.get("creditAccountActive", 0))
        closed_accounts = int(account_summary.get("creditAccountClosed", 0))
        defaulted_accounts = int(account_summary.get("creditAccountDefault", 0))

        # Aggregates
        total_credit_limit = 0
        total_current_balance = 0
        overdue_amounts = []

        for acct in details:
            credit_limit_str = acct.get("creditLimitAmount", "0")
            credit_limit = int(credit_limit_str.strip() if isinstance(credit_limit_str, str) else str(credit_limit_str) or "0")

            current_balance_str = acct.get("currentBalance", "0")
            current_balance = int(current_balance_str.strip() if isinstance(current_balance_str, str) else str(current_balance_str) or "0")

            past_due_str = acct.get("amountPastDue", "0")
            past_due = int(past_due_str.strip() if isinstance(past_due_str, str) else str(past_due_str) or "0")

            total_credit_limit += credit_limit
            total_current_balance += current_balance
            overdue_amounts.append(past_due)

        credit_utilization = (
            (total_current_balance / total_credit_limit) * 100
            if total_credit_limit > 0 else 0.0
        )

        score_val = score_info.get("bureauScore")
        if score_val is None or not str(score_val).strip().isdigit():
            score = 0  # or set to "N/A" if data type permits
        else:
            score = int(str(score_val).strip())

        flags = {
            "high_utilization": credit_utilization > 60,
            "avg_overdue_flag": mean(overdue_amounts) if overdue_amounts else 0 > 0
        }

        avg_overdue = mean(overdue_amounts) if overdue_amounts else 0

        return {
            "summary": {
                "userId": user_id,
                "totalAccounts": total_accounts,
                "activeAccounts": active_accounts,
                "closedAccounts": closed_accounts,
                "defaultedAccounts": defaulted_accounts,
                "totalCreditLimit": total_credit_limit,
                "totalCurrentBalance": total_current_balance,
                "creditUtilization": round(credit_utilization, 2),
                "avgOverdueAmount": avg_overdue,
                "creditScore": score,
                "flags": flags,
                "bureau": bureau
            }
        }

    except Exception as e:
        logger.error(f"[CreditProcessor] Failed to process credit report for user {user_id}: {e}")
        return {
            "summary": {
                "userId": user_id,
                "error": "Invalid credit report structure"
            }
        }
class CreditReportAnalyzer:
    @staticmethod
    def analyze(user_id: str, data: dict) -> dict:
        return process_credit_report(user_id, data)