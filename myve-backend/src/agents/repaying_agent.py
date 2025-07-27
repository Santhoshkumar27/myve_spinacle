"""
RepayingAgent

Role:
-----
Handles queries related to loan repayments, credit card dues, and billing obligations.

Responsibilities:
------------------
- Identify the most urgent dues or repayment priorities.
- Suggest optimal repayment strategies based on cash flow and outstanding debts.
- Recommend EMI prepayment or credit optimization steps if feasible.

Tools/Libs Used:
----------------
"""

import statistics
import math

from typing import Dict, Any, List
from pydantic import BaseModel
from src.agent_orchestrator import AgentDataOrchestrator
from src.schemas.repay import CreditAccount
from src.agents.assessment_agent import AssessmentAgent
from src.agents.response_agent import AgentResponse

def simulate_repayment_schedule(debts: List[CreditAccount], monthly_budget: float) -> List[str]:
    """
    Simulates monthly repayment distribution using the avalanche method.
    Returns human-readable schedule summary per account.
    """
    schedule = []
    remaining_budget = monthly_budget
    debts = sorted(debts, key=lambda x: -x.interest_rate)  # Avalanche priority

    for acc in debts:
        if acc.balance <= 0:
            continue
        months = math.ceil(acc.balance / remaining_budget) if remaining_budget else float('inf')
        schedule.append(f"→ {acc.bank_name}: ₹{acc.balance} will take approx. {months} month(s) to repay with ₹{monthly_budget}/mo.")
    return schedule

import logging

class RepayingAgent:
    def __init__(self):
        self.orchestrator = AgentDataOrchestrator()
        self.assessor = AssessmentAgent()

    def compare_strategies(self, debts: List[CreditAccount], monthly_budget: float) -> str:
        """
        Compares Snowball vs Avalanche methods for repayment.
        Returns a summary with pros/cons and timeline estimation.
        """
        def compute_months(debts_sorted):
            months = 0
            remaining = [acc.balance for acc in debts_sorted]
            while any(b > 0 for b in remaining):
                for i in range(len(remaining)):
                    if remaining[i] > 0:
                        payment = min(remaining[i], monthly_budget)
                        remaining[i] -= payment
                months += 1
            return months

        # Avalanche: High interest first
        avalanche_sorted = sorted(debts, key=lambda x: -x.interest_rate)
        avalanche_months = compute_months(avalanche_sorted)

        # Snowball: Smallest balance first
        snowball_sorted = sorted(debts, key=lambda x: x.balance)
        snowball_months = compute_months(snowball_sorted)

        summary = f"🔀 **Strategy Comparison**:\n"
        summary += f"- Avalanche (high interest first): clears in ~{avalanche_months} months.\n"
        summary += f"- Snowball (smallest balance first): clears in ~{snowball_months} months.\n"

        if avalanche_months < snowball_months:
            summary += "💡 Recommendation: Use the Avalanche method to save more on interest."
        elif snowball_months < avalanche_months:
            summary += "💡 Recommendation: Use the Snowball method for quicker motivation by closing accounts early."
        else:
            summary += "🎯 Both methods result in similar payoff time. Choose based on your preference!"

        return summary

    def run(self, prompt: str, user_id: str):
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"[RepayingAgent] Running for user {user_id}")
            logger.info(f"[RepayingAgent] Received prompt: {prompt} for user: {user_id}")
            raw_data = self.orchestrator.fetch_all_financial_data(user_id)
            if not isinstance(raw_data, dict):
                return AgentResponse(
                    response="Received malformed financial data.",
                    metadata={
                        "agent": "repaying",
                        "debts_considered": 0
                    }
                )
            # Fetch credit accounts from nested credit_summary['accounts'] with robust fallback
            import json
            credit_summary = raw_data.get("credit_summary", {})
            print("[DEBUG] Full credit summary:", json.dumps(credit_summary, indent=2))
            credit_accounts_raw = []
            if "accounts" in credit_summary and isinstance(credit_summary["accounts"], list):
                credit_accounts_raw = credit_summary["accounts"]
            elif "details" in credit_summary and isinstance(credit_summary["details"], list):
                credit_accounts_raw = credit_summary["details"]
            else:
                # Improved fallback: parse summary for account-like data
                summary_obj = credit_summary.get("summary", {})
                if isinstance(summary_obj, list):
                    if summary_obj:
                        summary_obj = summary_obj[0]
                    else:
                        summary_obj = {}
                if isinstance(summary_obj, dict) and "accounts" in summary_obj:
                    credit_accounts_raw = []
                    for acc in summary_obj["accounts"]:
                        credit_accounts_raw.append({
                            "bank": acc.get("bank_name", "Unknown"),
                            "balance": acc.get("balance", 0),
                            "interest_rate": acc.get("interest_rate", 8.5),
                            "limit": acc.get("limit", 0),
                            "overdue": acc.get("overdue", 0),
                            "opened_date": acc.get("opened_date"),
                            "roi": acc.get("interest_rate", 8.5)
                        })
                else:
                    account_like = {
                        "bank": summary_obj.get("bank_name", "Combined Credit Balance"),
                        "balance": summary_obj.get("totalCurrentBalance", 0),
                        "interest_rate": summary_obj.get("avgInterestRate", 8.5),
                        "limit": summary_obj.get("totalCreditLimit", 0),
                        "overdue": summary_obj.get("avgOverdueAmount", 0)
                    }
                    credit_accounts_raw = [account_like]
            print("[DEBUG] Effective credit_accounts_raw keys:", [k for k in credit_accounts_raw[0].keys()] if credit_accounts_raw else "No account data found")
            print("[DEBUG] Raw accounts extracted:", json.dumps(credit_accounts_raw, indent=2))
            summary_obj_debug = credit_summary.get("summary", {})
            if isinstance(summary_obj_debug, dict):
                print("[DEBUG] Keys in summary object:", list(summary_obj_debug.keys()))
            else:
                print("[DEBUG] Keys in summary object: [Invalid format - expected dict]")
            print("[DEBUG] Credit accounts from summary:", credit_accounts_raw)

            # --- Validate credit_accounts_raw before further processing ---
            if not isinstance(credit_accounts_raw, list) or not all(isinstance(acc, dict) for acc in credit_accounts_raw):
                logger.error(f"[RepayingAgent] credit_accounts_raw is malformed: {credit_accounts_raw}")
                return AgentResponse(
                    response="We encountered an issue with your credit data format.",
                    metadata={"agent": "repaying", "error": "credit_accounts_raw not list of dicts"}
                )

            user_credit = []
            for acc in credit_accounts_raw:
                try:
                    user_credit.append(CreditAccount(
                        bank_name=acc.get("bank_name") or acc.get("bank") or "Combined Credit Balance",
                        balance=acc.get("balance", 0),
                        interest_rate=acc.get("interest_rate", 0),
                        limit=acc.get("limit", 0),
                        overdue=acc.get("overdue", 0),
                        opened_date=acc.get("opened_date", None),
                        roi=acc.get("interest_rate", 0)
                    ))
                    print("[DEBUG] Successfully parsed credit account:", acc.get("bank_name") or acc.get("bank") or "Combined Credit Balance")
                except Exception as e:
                    print("[ERROR] Failed to parse credit account:", e)
            if not user_credit:
                return AgentResponse(
                    response="We couldn't retrieve your credit data at the moment. Please try again later.",
                    metadata={
                        "agent": "repaying",
                        "debts_considered": 0
                    }
                )

            bank_summary = raw_data.get("bank_summary", {})
            if isinstance(bank_summary, dict):
                bank_data_raw = bank_summary.get("summary", [])
            else:
                bank_data_raw = []
            if isinstance(bank_data_raw, str):
                try:
                    bank_data = json.loads(bank_data_raw)
                except Exception:
                    logger.error(f"[RepayingAgent] Failed to parse bank data JSON string: {bank_data_raw}")
                    bank_data = []
            elif isinstance(bank_data_raw, dict):
                bank_data = [bank_data_raw]
            elif isinstance(bank_data_raw, list):
                bank_data = bank_data_raw
            else:
                logger.warning(f"[RepayingAgent] Unexpected bank data format: {type(bank_data_raw)}")
                bank_data = []
            print("[DEBUG] Bank summary data:", json.dumps(bank_data, indent=2))
            monthly_inflow = 0
            monthly_outflow = 0
            if isinstance(bank_data, list) and len(bank_data) > 0 and isinstance(bank_data[0], dict):
                monthly_inflow = bank_data[0].get("totalCredits", 0)
                monthly_outflow = bank_data[0].get("totalDebits", 0)
            else:
                logger.warning(f"[RepayingAgent] Bank data format invalid or empty: {type(bank_data)}")
            disposable_income = monthly_inflow - monthly_outflow

            # --- Insert validation for stock["txns"] before any processing ---
            stock = raw_data.get("stock", {})
            valid_txns = []
            if isinstance(stock, dict):
                for txn in stock.get("txns", []):
                    if isinstance(txn, list) and len(txn) == 4:
                        valid_txns.append(txn)
                    else:
                        logger.warning(f"[RepayingAgent] Ignored malformed stock txn: {txn}")
            else:
                logger.warning(f"[RepayingAgent] stock is not a dict: {type(stock)}")
            # From here on, use valid_txns instead of stock["txns"] for calculations

            # Sort by urgency: overdue > interest_rate > balance
            sorted_debts = sorted(user_credit, key=lambda x: (x.overdue == 0, -x.interest_rate, -x.balance))

            recommendations = []
            for acc in sorted_debts:
                action = (
                    f"⚠️ Pay off your {acc.bank_name} card soon. ₹{acc.overdue} is overdue with {acc.interest_rate}% interest."
                    if acc.overdue > 0 else
                    f"💡 Consider prepaying your {acc.bank_name} balance of ₹{acc.balance} to avoid {acc.interest_rate}% interest buildup."
                )
                recommendations.append(action)

            # Ensure credit_data is defined for utilization warnings
            credit_data = credit_accounts_raw if isinstance(credit_accounts_raw, list) else []
            # Utilization warnings (robust for dicts and objects)
            utilization_warnings = []
            for entry in credit_data:
                try:
                    if isinstance(entry, dict):
                        limit = entry.get("limit")
                        balance = entry.get("balance", 0)
                        bank_name = entry.get("bank_name", entry.get("bank", "Unknown"))
                    else:  # Pydantic model or object
                        limit = getattr(entry, "limit", None)
                        balance = getattr(entry, "balance", 0)
                        bank_name = getattr(entry, "bank_name", getattr(entry, "bank", "Unknown"))

                    if limit and limit > 0 and (balance / limit) > 0.3:
                        utilization_warnings.append(
                            f"⚠️ High credit utilization on {bank_name}. Consider reducing usage to protect your credit score."
                        )
                except Exception as e:
                    logger.warning(f"[RepayingAgent] Failed to assess utilization for entry: {entry} — {e}")

            if utilization_warnings:
                recommendations += utilization_warnings

            balances = [acc.balance for acc in user_credit]
            overdue_amounts = [acc.overdue for acc in user_credit if acc.overdue > 0]
            interest_rates = [acc.interest_rate for acc in user_credit]

            stats_summary = ""
            if balances:
                stats_summary += f"\n\n📊 Average balance across credit accounts: ₹{math.floor(statistics.mean(balances))}"
            if overdue_amounts:
                stats_summary += f"\n📌 Total overdue amount: ₹{math.floor(sum(overdue_amounts))}"
            if interest_rates:
                stats_summary += f"\n📈 Highest interest rate: {max(interest_rates)}%"

            stats_summary += f"\n💰 Monthly disposable income: ₹{math.floor(disposable_income)}"

            total_debt = sum(overdue_amounts)
            if disposable_income > 0 and total_debt > 0:
                months_to_repay = math.ceil(total_debt / disposable_income)
                stats_summary += f"\n🗓 Estimated months to repay all dues: {months_to_repay} month(s)"

            summary = "🔍 **Repayment Recommendations:**\n" + "\n".join(recommendations)
            simulation_output = ""
            if disposable_income > 0:
                sim_schedule = simulate_repayment_schedule(user_credit, disposable_income)
                if sim_schedule:
                    simulation_output += "\n\n📅 **Payoff Simulation:**\n" + "\n".join(sim_schedule)

            strategy_output = ""
            if disposable_income > 0:
                strategy_output = "\n\n🔍 " + self.compare_strategies(user_credit, disposable_income)

            payoff_structure = []
            if disposable_income > 0:
                for acc in sorted_debts:
                    logger.debug(f"[RepayingAgent] Generating recommendation for account: {acc.bank_name}")
                    if acc.balance <= 0:
                        continue
                    months = math.ceil(acc.balance / disposable_income)
                    payoff_structure.append({
                        "bank": acc.bank_name,
                        "balance": acc.balance,
                        "estimated_months": months
                    })

            # Request behavioral overlay with financial stability, risk, and suggestions
            try:
                logger.debug("[RepayingAgent] Calling assessment agent for behavioral overlay")
                assessment_output = self.assessor.run(
                    prompt=f"Assess user repayment behavior and risk for credit optimization. Prompt: {prompt}",
                    user_id=user_id,
                    required_data_keys=["bank", "credit", "mf", "epf", "networth", "stock"]
                )
                if isinstance(assessment_output, dict):
                    report = assessment_output.get("assessment", {})
                else:
                    report = getattr(assessment_output, "metadata", {}).get("assessment", {})
            except Exception as e:
                print(f"[RepayingAgent] Skipping behavioral flags due to: {e}")
                report = {}
            behavioral_overlay = ""
            if report:
                income_stability = report.get("incomeStabilityScore")
                savings_ratio = report.get("savingsToIncomeRatio")
                debt_ratio = report.get("debtToIncomeRatio")
                emergency_fund = report.get("emergencyFundStatus")
                risk_flags = report.get("riskFlags", [])
                recommendations = report.get("recommendations", [])

                behavioral_overlay += "\n\n🧠 **Behavioral Insights:**"
                if income_stability:
                    behavioral_overlay += f"\n✅ Income stability score: {income_stability}"
                if savings_ratio:
                    behavioral_overlay += f"\n💼 Savings to income ratio: {savings_ratio}"
                if debt_ratio:
                    behavioral_overlay += f"\n📉 Debt to income ratio: {debt_ratio}"
                if emergency_fund:
                    behavioral_overlay += f"\n🛡️ Emergency fund: {emergency_fund}"
                if risk_flags:
                    behavioral_overlay += f"\n⚠️ Risk flags: {', '.join(risk_flags)}"
                if recommendations:
                    behavioral_overlay += f"\n📌 Suggestions: {', '.join(recommendations)}"

            logger.info(f"[RepayingAgent] Response summary generated for user {user_id}")
            # Debug logs for response structure
            logger.info(f"[RepayingAgent] Final response payload: {summary + stats_summary + simulation_output + strategy_output + behavioral_overlay}")
            logger.info(f"[RepayingAgent] Metadata payload: {payoff_structure}")
            full_response = AgentResponse(
                response=summary + "\n\n📈 **Repayment Overview:**" + stats_summary + simulation_output + strategy_output + behavioral_overlay,
                metadata={
                    "agent": "repaying",
                    "debts_considered": len(user_credit),
                    "payoff_structure": payoff_structure
                }
            )
            logger.info(f"[RepayingAgent] Full response object: {full_response}")
            return full_response
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"[RepayingAgent] Error during debt analysis: {e}")
            return AgentResponse(
                response="We encountered an issue while evaluating your debts.",
                metadata={"agent": "repaying", "error": str(e)}
            )




    def __call__(self, prompt: str, user_id: str, required_data_keys: list[str] = []):
        return self.run(prompt, user_id)