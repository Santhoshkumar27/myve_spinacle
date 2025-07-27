"""
AssessmentAgent

Role:
--------
The AssessmentAgent analyzes the user's financial behavior and profile in a mathematically rigorous and logic-driven manner. It acts as the core observer and analyzer of the system.

Responsibilities:
------------------
- Collect and normalize data from multiple sources: net worth, income, expenses, credit reports, assets, liabilities, bank transactions.
- Perform financial behavior profiling: spending patterns, debt management, income stability.
- Identify critical financial risks: high EMI burdens, credit card overuse, overdue debts.
- Provide context-aware analysis for other agents: especially PlanningAgent and BuyingAgent.
- Maintain a stable, structured JSON snapshot of the user’s financial health ("assessment report") which can be shared with other agents.

Key Features:
--------------
- Anomaly detection in spending/saving patterns.
- Real-time trend analysis using monthlyTrend and cash flow.
- Debt-to-income and credit utilization ratio calculators.
- Savings adequacy metrics (emergency funds, insurance gaps).
- Behavioural flags (e.g. overspending signals, risky credit behavior).

Tools/Libs Used:
----------------
- NumPy / pandas for statistical and trend analysis.
- dateutil for time-based behavior modeling.
- sklearn (optional) for predictive scoring models (e.g. spending deviation).
- jsonschema for validating and maintaining assessment reports.
- Rich/loguru for detailed tracing/debugging logs.
"""

# Additional imports for assessment agent
import pandas as pd
import numpy as np
from dateutil import parser
from src.agent_orchestrator import AgentDataOrchestrator
from loguru import logger
from sklearn.ensemble import IsolationForest
from jsonschema import validate, ValidationError
import json
from src.services.gemini_service import askassess  # or the appropriate path to Gemini integration


class AssessmentAgent:
    def __call__(self, prompt: str, user_id: str, required_data_keys: list[str]):
        return self.run(prompt, user_id, required_data_keys)
    def __init__(self):
        self.role = "Assess user’s complete financial health using structured data. Acts as the observation layer for all downstream financial intelligence agents."
        self.orchestrator = AgentDataOrchestrator()
        self.logger = logger.bind(agent="AssessmentAgent")

    def normalize_summary(self, data_item):
        if isinstance(data_item, list):
            return data_item[0] if data_item and isinstance(data_item[0], dict) else {}
        return data_item if isinstance(data_item, dict) else {}

    def run(self, prompt: str, user_id: str, required_data_keys: list[str]):
        from src.agents.response_agent import AgentResponse
        try:
            self.logger.info(f"Running assessment for user {user_id}")
            data = self.orchestrator.fetch_all_financial_data(user_id)
            if not data or not isinstance(data, dict):
                raise ValueError("No structured financial data received from orchestrator")

            networth_raw = {}
            if "networth" in required_data_keys:
                net_summary = data.get("networth_summary", {})
                if isinstance(net_summary, dict):
                    if "summary" in net_summary:
                        summary_val = net_summary["summary"]
                        if isinstance(summary_val, list):
                            networth_raw = summary_val[0] if summary_val else {}
                        elif isinstance(summary_val, dict):
                            networth_raw = summary_val
                    else:
                        networth_raw = net_summary

            bank_data = self.normalize_summary(data.get("bank_summary", {}).get("summary", {})) if "bank" in required_data_keys else {}
            credit_data = self.normalize_summary(data.get("credit_summary", {}).get("summary", {})) if "credit" in required_data_keys else {}
            mf_data = self.normalize_summary(data.get("mf_summary", {}).get("summary", {})) if "mf" in required_data_keys else {}
            epf_data = self.normalize_summary(data.get("epf_summary", {}).get("summary", {})) if "epf" in required_data_keys else {}
            stock_data = self.normalize_summary(data.get("stock", {})) if "stock" in required_data_keys else {}

 

            monthly = data.get("monthly", []) if "bank" in required_data_keys or "mf" in required_data_keys else []
            income = data.get("income", 0) if "bank" in required_data_keys else 0
            savings = data.get("savings", 0) if "bank" in required_data_keys else 0
            debt = data.get("debt", 0) if "bank" in required_data_keys else 0
            expenses = data.get("expenses", 0) if "bank" in required_data_keys else 0
            incomeTrend = data.get("incomeTrend", []) if "bank" in required_data_keys else []

            filtered_data = {
                "networth": networth_raw,
                "bank": bank_data,
                "credit": credit_data,
                "mf": mf_data,
                "epf": epf_data,
                "stock": stock_data,
                "monthly": monthly,
                "income": income,
                "savings": savings,
                "debt": debt,
                "expenses": expenses,
                "incomeTrend": incomeTrend,
            }

            report = self.generate_assessment_report(filtered_data)
            ai_summary = self.generate_ai_summary(user_id, filtered_data, report, prompt)
            return AgentResponse(
                response=ai_summary if ai_summary else self.format_summary(report),
                metadata={"agent": "assess", "assessment": report, "ai_summary": ai_summary}
            )
        except Exception as e:
            self.logger.exception("AssessmentAgent failed")
            return AgentResponse(
                response="Sorry, something went wrong during assessment.",
                metadata={"agent": "assess", "error": str(e)}
            )

    def generate_assessment_report(self, data: dict) -> dict:
        mf_data = data.get("mf", {})
        if isinstance(mf_data, list):
            mf_data = mf_data[0] if mf_data else {}

        trend = data.get("monthly", [])
        # Extract user_id for logging context
        user_id = data.get("bank", {}).get("userId", "N/A")

        # Fallback math for incomplete data
        income = data.get("income", 0)
        savings = data.get("savings", 0)
        debt = data.get("debt", 0)
        expenses = data.get("expenses", 0)

        avg_income_est = None
        if income == 0:
            trend_vals = [month.get("value", 0) for month in trend if "value" in month]
            if len(trend_vals) >= 3:
                avg_income_est = np.mean(trend_vals[-3:])
                income = avg_income_est
                self.logger.info(f"[AssessmentAgent] Income estimated from bank monthlyTrend: {income}")
            elif mf_data.get("monthlyReturns"):
                mf_vals = list(mf_data["monthlyReturns"].values())
                if len(mf_vals) >= 3:
                    avg_income_est = np.mean(mf_vals[-3:])
                    income = avg_income_est
                    self.logger.info(f"[AssessmentAgent] Income estimated from MF monthlyReturns: {income}")

        if savings == 0 and avg_income_est:
            savings = avg_income_est * 0.15
            self.logger.info(f"[AssessmentAgent] Savings estimated from income fallback: {savings}")
        if expenses == 0 and avg_income_est:
            expenses = avg_income_est * 0.8
            self.logger.info(f"[AssessmentAgent] Expenses estimated from income fallback: {expenses}")

        anomalies = self.detect_anomalies_in_trend(trend)

        # Flatten net worth
        networth_raw = data.get("networth", {})
        networth_resp = networth_raw
        net_worth_value = {}

        if isinstance(networth_resp, dict):
            # Prioritize direct totalNetWorth if available
            if "totalNetWorth" in networth_resp:
                net_worth_value = networth_resp["totalNetWorth"]
            elif "totalNetWorthValue" in networth_resp:
                net_worth_value = networth_resp["totalNetWorthValue"]
            else:
                for key in ["netWorth", "data"]:
                    val = networth_resp.get(key)
                    if isinstance(val, dict) and "units" in val:
                        net_worth_value = val
                        break

        income_stability = self.compute_income_stability(data.get("incomeTrend", []))
        savings_ratio = self.compute_savings_to_income_ratio(savings, income)
        debt_ratio = self.compute_debt_to_income_ratio(debt, income)
        emergency_status = self.evaluate_emergency_fund_sufficiency(savings, expenses)

        # Logging computed fields for traceability
        self.logger.info(f"[AssessmentAgent] Income Stability Score for {user_id}: {income_stability}")
        self.logger.info(f"[AssessmentAgent] Savings to Income Ratio for {user_id}: {savings_ratio}%")
        self.logger.info(f"[AssessmentAgent] Debt to Income Ratio for {user_id}: {debt_ratio}%")
        self.logger.info(f"[AssessmentAgent] Emergency Fund Status for {user_id}: {emergency_status}")

        report = {
            "netWorth": net_worth_value,
            "creditUtilization": self.compute_credit_utilization(data.get("networth", {}).get("data", {}).get("accounts", {})),
            "monthlyTrend": trend,
            "riskFlags": ["Anomaly in spending trend"] if anomalies else [],
            "recommendations": ["Review your recent financial activity."] if anomalies else []
        }

        report.update({
            "incomeStabilityScore": income_stability,
            "savingsToIncomeRatio": savings_ratio,
            "debtToIncomeRatio": debt_ratio,
            "emergencyFundStatus": emergency_status
        })
        report["behaviorProfile"] = {
            "incomeStability": income_stability,
            "savingsRatio": savings_ratio,
            "debtToIncome": debt_ratio,
            "emergencyStatus": emergency_status
        }  # Used by downstream agents like RepayingAgent
        report["behaviorFlags"] = report.get("riskFlags", [])  # Reusing risk flags instead of undefined method

        # --- Additional Insights ---
        extra_insights = {}

        # Stock portfolio analysis (basic)
        stock_data = data.get("stock", {})
        if stock_data.get("txns"):
            stock_df = pd.DataFrame(stock_data["txns"], columns=["txn_type", "date", "qty", "price"])
            stock_df["date"] = pd.to_datetime(stock_df["date"])
            stock_df["amount"] = stock_df["qty"] * stock_df["price"]

            buy_amount = stock_df[stock_df["txn_type"] == 1]["amount"].sum()
            sell_amount = stock_df[stock_df["txn_type"] == 2]["amount"].sum()
            current_qty = stock_df[stock_df["txn_type"] == 1]["qty"].sum() - stock_df[stock_df["txn_type"] == 2]["qty"].sum()
            avg_buy_price = (
                stock_df[stock_df["txn_type"] == 1].apply(lambda row: row["qty"] * row["price"], axis=1).sum()
                / stock_df[stock_df["txn_type"] == 1]["qty"].sum()
                if stock_df[stock_df["txn_type"] == 1]["qty"].sum() > 0 else 0
            )
            extra_insights["StockHoldings"] = {
                "totalInvestment": round(buy_amount, 2),
                "realizedReturns": round(sell_amount - buy_amount, 2),
                "avgBuyPrice": round(avg_buy_price, 2),
                "unitsHeld": int(current_qty)
            }

        # Mutual fund investment summary
        mf = data.get("mf", {})
        if isinstance(mf, dict) and "summaryByType" in mf:
            mf_summary = mf["summaryByType"]
            extra_insights["MutualFundAllocation"] = {
                "Equity": mf_summary.get("Equity", 0),
                "Debt": mf_summary.get("Debt", 0),
                "Hybrid": mf_summary.get("Hybrid", 0),
                "Thematic": mf_summary.get("Thematic", 0),
                "Commodities": mf_summary.get("Commodities", 0)
            }

        # Add insight summary to final report
        report["insights"] = extra_insights

        if savings_ratio < 20:
            report["recommendations"].append("Consider increasing your emergency savings.")
        if income_stability < 50:
            report["riskFlags"].append("Income appears unstable.")
        if debt_ratio > 40:
            report["riskFlags"].append("High debt-to-income ratio may be risky.")
        if emergency_status == "Insufficient":
            report["recommendations"].append("Build an emergency fund to cover at least 3 months of expenses.")

        if not self.validate_assessment_schema(report):
            self.logger.error("Generated report is invalid against schema.")

        return report

    def compute_credit_utilization(self, accounts: dict) -> float:
        total_limit = 0
        total_used = 0
        for acc in accounts.values():
            if acc.get("accountDetails", {}).get("accInstrumentType") == "ACC_INSTRUMENT_TYPE_CREDIT_CARD":
                credit = acc.get("creditCardSummary", {})
                total_limit += float(credit.get("creditLimit", {}).get("units", 0) or 0)
                total_used += float(credit.get("currentBalance", {}).get("units", 0) or 0)
        if total_limit == 0:
            return 0.0
        return round((total_used / total_limit) * 100, 2)

    def format_summary(self, report: dict) -> str:
        net_obj = report.get("netWorth", {})
        net_val = None
        units_val = None
        # Try to extract 'units' from netWorth object, handling missing/malformed values
        if isinstance(net_obj, dict):
            # Try direct 'units'
            units_val = net_obj.get("units")
            # If not, check for nested dicts
            if units_val is None:
                if isinstance(net_obj.get("data"), dict):
                    units_val = net_obj.get("data", {}).get("units")
            # Fallback to 'formatted' field if still None
            if units_val is None:
                units_val = net_obj.get("formatted")
            # Fallback to 'value' or nested 'value'
            if units_val is None:
                units_val = net_obj.get("value") or (net_obj.get("data", {}).get("value") if isinstance(net_obj.get("data"), dict) else None)
        # If still not found, fallback to "N/A"
        if units_val is None:
            units_val = "N/A"
        # Now format the number
        try:
            if isinstance(units_val, (int, float)):
                net = f"{int(float(units_val)):,}"
            elif isinstance(units_val, str):
                cleaned = units_val.replace(",", "").replace("₹", "").strip()
                # Accept numbers with decimals, ignore if not a number
                float_val = None
                try:
                    float_val = float(cleaned)
                except Exception:
                    float_val = None
                net = f"{int(float_val):,}" if float_val is not None else "N/A"
            else:
                net = "N/A"
        except Exception as e:
            self.logger.warning(f"Net worth formatting failed: {e}")
            net = "N/A"

        credit_util = report.get("creditUtilization", "N/A")
        trend = report.get("monthlyTrend", [])
        growth = "N/A"
        if len(trend) >= 2:
            try:
                first = float(trend[0]["value"])
                last = float(trend[-1]["value"])
                growth = f"{((last - first) / first) * 100:.2f}%" if first else "N/A"
            except Exception as e:
                self.logger.warning(f"Monthly growth computation failed: {e}")
        return (
            f"Here’s a quick snapshot of your finances:\n"
            f"- Net Worth: ₹{net}\n"
            f"- Credit Utilization: {credit_util}%\n"
            f"- Monthly Growth: {growth}\n"
            f"- Income Stability Score: {report.get('incomeStabilityScore', 'N/A')}%\n"
            f"- Savings to Income Ratio: {report.get('savingsToIncomeRatio', 'N/A')}%\n"
            f"- Debt to Income Ratio: {report.get('debtToIncomeRatio', 'N/A')}%\n"
            f"- Emergency Fund Status: {report.get('emergencyFundStatus', 'N/A')}"
        )

    def detect_anomalies_in_trend(self, trend: list) -> list:
        if not trend or len(trend) < 6:
            return []

        df = pd.DataFrame(trend)
        df['month'] = pd.to_datetime(df['month'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df.dropna(inplace=True)

        model = IsolationForest(contamination=0.2, random_state=42)
        df['anomaly'] = model.fit_predict(df[['value']])
        anomalies = df[df['anomaly'] == -1]

        return anomalies[['month', 'value']].to_dict(orient='records')

    def validate_assessment_schema(self, report: dict) -> bool:
        schema = {
            "type": "object",
            "properties": {
                "netWorth": {"type": "object"},
                "creditUtilization": {"type": "number"},
                "monthlyTrend": {"type": "array"},
                "riskFlags": {"type": "array"},
                "recommendations": {"type": "array"},
                "incomeStabilityScore": {"type": "number"},
                "savingsToIncomeRatio": {"type": "number"},
                "debtToIncomeRatio": {"type": "number"},
                "emergencyFundStatus": {"type": "string"}
            },
            "required": [
                "netWorth",
                "creditUtilization",
                "monthlyTrend",
                "incomeStabilityScore",
                "savingsToIncomeRatio",
                "debtToIncomeRatio",
                "emergencyFundStatus"
            ]
        }
        try:
            validate(instance=report, schema=schema)
            return True
        except ValidationError as ve:
            self.logger.warning(f"Assessment report schema validation failed: {ve}")
            return False

    def compute_income_stability(self, income_records: list) -> float:
        """Computes income stability score based on std deviation over months."""
        if not income_records or len(income_records) < 3:
            return 0.0
        df = pd.DataFrame(income_records)
        df['month'] = pd.to_datetime(df['month'])
        df['income'] = pd.to_numeric(df['income'], errors='coerce')
        df.dropna(inplace=True)
        return round(100 - (df['income'].std() / df['income'].mean()) * 100, 2)

    def compute_savings_to_income_ratio(self, savings: float, income: float) -> float:
        if income == 0:
            return 0.0
        return round((savings / income) * 100, 2)

    def compute_debt_to_income_ratio(self, debt: float, income: float) -> float:
        if income == 0:
            return 0.0
        return round((debt / income) * 100, 2)

    def evaluate_emergency_fund_sufficiency(self, savings: float, expenses: float) -> str:
        if expenses == 0:
            return "Unknown"
        months_covered = savings / expenses
        if months_covered >= 6:
            return "Adequate"
        elif months_covered >= 3:
            return "Moderate"
        else:
            return "Insufficient"

    def get_role(self) -> str:
        return self.role
    def generate_ai_summary(self, user_id: str, financial_data: dict, report: dict, user_question: str) -> str:
        """
        Generates an AI summary using the user's question and financial data.
        Ensures the actual user_question is passed as the prompt to the assessment agent.
        Adds fallback mechanism for general financial queries (e.g., tools/strategies).
        """
        try:
            # Include extra computed estimates from report to give Gemini more context
            enriched_data = financial_data.copy()
            enriched_data.update({
                "incomeStabilityScore": report.get("incomeStabilityScore"),
                "savingsToIncomeRatio": report.get("savingsToIncomeRatio"),
                "debtToIncomeRatio": report.get("debtToIncomeRatio"),
                "emergencyFundStatus": report.get("emergencyFundStatus"),
                # Add logged summaries for more context to Gemini
                "bankSummary": financial_data.get("bank"),
                "creditSummary": financial_data.get("credit"),
                "mfSummary": financial_data.get("mf"),
                "epfSummary": financial_data.get("epf"),
                "stockSummary": financial_data.get("stock"),
            })


            # Fallback: If the question is broad/general advice, simplify the context
            # Minimal context: only send bank/expense trends if question is about tools/strategies/recommendations
            if (
                "tool" in user_question.lower()
                or "strategy" in user_question.lower()
                or "recommend" in user_question.lower()
            ):
                minimal_context = {
                    "monthlyTrend": financial_data.get("monthly", []),
                    "bankSummary": financial_data.get("bank", {}),
                    "expenses": financial_data.get("expenses", 0)
                }
                enriched_data = minimal_context

            # If the question is about repayment, provide fallback context
            if "repay" in user_question.lower():
                enriched_data = {
                    "bank": financial_data.get("bank"),
                    "credit": financial_data.get("credit"),
                    "debtToIncomeRatio": report.get("debtToIncomeRatio"),
                    "savingsToIncomeRatio": report.get("savingsToIncomeRatio")
                }

            # Ensure the user_question is explicitly passed as the prompt parameter
            ai_response = askassess(prompt=user_question, financial_data=enriched_data)

            # Fallback logic if Gemini fails
            if isinstance(ai_response, dict):
                return ai_response.get("text", self.format_summary(report))
            return str(ai_response).strip() if ai_response else self.format_summary(report)

        except Exception as e:
            self.logger.error(f"[AssessmentAgent] Gemini insight generation failed: {e}")
            return "We're unable to generate AI-driven financial insights right now. Please try again later."


    def get_snapshot(self, user_id: str) -> dict:
        """
        Returns the latest available assessment snapshot for this user.
        This is a minimal method to allow generic query resolution when detailed answers are unavailable.
        """
        try:
            data = self.orchestrator.fetch_all_financial_data(user_id)
            return {
                "networth": data.get("networth_summary", {}),
                "bank": data.get("bank_summary", {}),
                "credit": data.get("credit_summary", {}),
                "mf": data.get("mf_summary", {}),
                "epf": data.get("epf_summary", {}),
                "stock": data.get("stock", {})
            }
        except Exception as e:
            self.logger.error(f"[AssessmentAgent] Failed to fetch snapshot for {user_id}: {e}")
            return {}
