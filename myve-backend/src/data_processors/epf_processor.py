import logging

logger = logging.getLogger(__name__)

def process_epf_data(user_id, epf_data):
    """
    Processes EPF data and returns an EPF summary dictionary.
    """
    logger.info(f"[EPF Processor] Processing EPF data for user {user_id}")

    if not epf_data or "uanAccounts" not in epf_data or not epf_data["uanAccounts"]:
        logger.warning(f"[EPF Processor] No EPF data found for user {user_id}")
        return {
            "summary": {
                "total_pf_balance": 0,
                "pension_balance": 0,
                "employee_total": 0,
                "employer_total": 0,
                "establishment_count": 0
            }
        }

    try:
        raw_details = epf_data["uanAccounts"][0].get("rawDetails", {})
        overall = raw_details.get("overall_pf_balance", {})
        est_details = raw_details.get("est_details", [])

        return {
            "summary": {
                "total_pf_balance": int(overall.get("current_pf_balance", 0)),
                "pension_balance": int(overall.get("pension_balance", 0)),
                "employee_total": int(overall.get("employee_share_total", {}).get("balance", 0)),
                "employer_total": int(overall.get("employer_share_total", {}).get("balance", 0)),
                "establishment_count": len(est_details)
            }
        }

    except Exception as e:
        logger.error(f"[EPF Processor] Failed to process EPF data: {e}")
        return {
            "summary": {
                "total_pf_balance": 0,
                "pension_balance": 0,
                "employee_total": 0,
                "employer_total": 0,
                "establishment_count": 0
            }
        }

class EPFAnalyzer:
    """
    Analyzes EPF-related financial data for a given user.
    Wraps the process_epf_data logic for structured access.
    """

    @staticmethod
    def analyze(user_id: str, epf_data: dict) -> dict:
        return process_epf_data(user_id, epf_data)