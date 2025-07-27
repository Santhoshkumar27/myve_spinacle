from src.services.gemini_service import ask_gemini
from src.utils.web_search import fetch_perplexity_insights
from src.agent_orchestrator import AgentDataOrchestrator
import logging

logger = logging.getLogger(__name__)

class DataAgent:
    def __init__(self):
        self.orchestrator = AgentDataOrchestrator()

    def get_scenarios_for_user(self, user_id: str) -> dict:
        try:
            data = self.orchestrator.fetch_all_financial_data(user_id)
            snapshot = data.get("final_snapshot", {})
            income = snapshot.get("income", 0)
            debt = snapshot.get("debt", 0)
            savings = snapshot.get("savings", 0)

            scenarios = {
                "6_month_repayment_plan": {
                    "total_debt": debt,
                    "monthly_target": round(debt / 6, 2) if debt else 0,
                    "feasible": income > (debt / 6) if debt else False
                },
                "car_savings_plan": {
                    "target_amount": 500000,
                    "monthly_savings_needed": round(500000 / 12, 2),
                    "feasible": (income - snapshot.get("expenses", 0)) > (500000 / 12)
                },
                "emergency_fund_status": {
                    "current_savings": savings,
                    "recommended": round(income * 6, 2),
                    "adequate": savings >= (income * 6)
                },
                "llm_networth_plan": self.simulate_via_llm(
                    user_id,
                    "How can I grow my net worth to ₹1 crore in 5 years?",
                    use_perplexity=False
                ).get("llm_report", ""),
                "llm_monthly_investment_pathway": self.simulate_via_llm(
                    user_id,
                    "Suggest a ₹10,000 per month investment strategy for long-term growth",
                    use_perplexity=False
                ).get("llm_report", ""),
                "llm_smart_savings_strategy": self.simulate_via_llm(
                    user_id,
                    "What is a smart ₹20,000 per month savings strategy for short-term and long-term goals?",
                    use_perplexity=False
                ).get("llm_report", ""),
                "llm_two_year_debt_free_plan": self.simulate_via_llm(
                    user_id,
                    "How can I become debt-free in 2 years?",
                    use_perplexity=False
                ).get("llm_report", "")
            }

            scenarios.update({
                "repayment_plan_6_months": self.simulate_goal_pathway(user_id, "repay_in_X_months", {"months": 6}),
                "repayment_plan_12_months": self.simulate_goal_pathway(user_id, "repay_in_X_months", {"months": 12}),
                "networth_plan_2_years": self.simulate_via_llm(user_id, "How can I grow my net worth in 2 years?", use_perplexity=False).get("llm_report", ""),
                "networth_plan_5_years": self.simulate_via_llm(user_id, "How can I grow my net worth in 5 years?", use_perplexity=False).get("llm_report", "")
            })

            return scenarios
        except Exception as e:
            logger.error(f"[DataAgent] Error generating scenarios for {user_id}: {e}")
            return {}

    def simulate_goal_pathway(self, user_id: str, goal_type: str, params: dict = {}) -> dict:
        try:
            snapshot = self.orchestrator.fetch_all_financial_data(user_id).get("final_snapshot", {})
            income = snapshot.get("income", 0)
            savings = snapshot.get("savings", 0)
            debt = snapshot.get("debt", 0)

            if goal_type == "repay_in_X_months":
                months = int(params.get("months", 6))
                return {
                    "total_debt": debt,
                    "monthly_target": round(debt / months, 2) if debt else 0,
                    "feasible": income > (debt / months) if debt else False,
                    "goal": f"Repay ₹{debt} in {months} months"
                }

            elif goal_type == "save_for_goal":
                target_amount = float(params.get("target_amount", 500000))
                months = int(params.get("months", 12))
                monthly_savings_needed = round(target_amount / months, 2)
                feasible = (income - snapshot.get("expenses", 0)) > monthly_savings_needed
                return {
                    "target_amount": target_amount,
                    "monthly_savings_needed": monthly_savings_needed,
                    "feasible": feasible,
                    "goal": f"Save ₹{target_amount} in {months} months"
                }

            elif goal_type == "emergency_fund_check":
                recommended = round(income * 6, 2)
                adequate = savings >= recommended
                return {
                    "current_savings": savings,
                    "recommended": recommended,
                    "adequate": adequate,
                    "goal": "Emergency fund status"
                }

            else:
                return { "error": "Unsupported goal type." }

        except Exception as e:
            logger.error(f"[DataAgent] Simulation error for {user_id} on {goal_type}: {e}")
            return { "error": str(e) }

    def simulate_via_llm(self, user_id: str, query: str, use_perplexity=False, llm_model: str = "gemini") -> dict:
        try:
            snapshot = self.orchestrator.fetch_all_financial_data(user_id).get("final_snapshot", {})
            income = snapshot.get("income", 0)
            expenses = snapshot.get("expenses", 0)
            savings = snapshot.get("savings", 0)
            debt = snapshot.get("debt", 0)
            networth = snapshot.get("networth", 0)

            prompt = f"""
You are an advanced financial simulation agent. Based on the user's financial profile below, generate a clear simulation strategy:

💼 Financial Profile:
- Income: ₹{income}
- Expenses: ₹{expenses}
- Savings: ₹{savings}
- Debt: ₹{debt}
- Net Worth: ₹{networth}

📌 User's Simulation Request:
\"{query}\"

🎯 Your Output Should Include:
1. **Feasibility** — Is this financially possible now or later?
2. **Timeline** — How long would it realistically take?
3. **Monthly Targets** — Recommended monthly investment/savings/repayment amount.
4. **Risk Factors** — What are the financial or lifestyle risks involved?
5. **Final Recommendation** — Smart next step for the user to act on.

✅ Use structured formatting, spacing, and **bold key numbers**. Avoid fluff. This will power an AI simulator for real users.
"""

            result = None
            if llm_model == "gemini":
                result = ask_gemini(prompt)
            elif llm_model == "perplexity":
                result = fetch_perplexity_insights(prompt)

            perplexity_summary = None
            if use_perplexity and llm_model != "perplexity":
                try:
                    perplexity_summary = fetch_perplexity_insights(f"Financial planning for: {query}")
                except Exception as e:
                    logger.warning(f"[DataAgent] Perplexity fetch failed: {e}")

            return {
                "llm_report": result,
                "perplexity_summary": perplexity_summary,
                "metadata": {
                    "income": income,
                    "expenses": expenses,
                    "savings": savings,
                    "debt": debt,
                    "networth": networth
                }
            }

        except Exception as e:
            logger.error(f"[DataAgent] simulate_via_llm error for {user_id}: {e}")
            return { "error": str(e) }