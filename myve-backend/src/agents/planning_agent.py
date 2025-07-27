"""
PlanningAgent

Role:
--------
The PlanningAgent formulates strategic, mathematically sound action plans based on goals (buying, saving, investing). It works closely with the AssessmentAgent to construct feasible roadmaps.

Responsibilities:
------------------
- Receive "planning request" from ResponseAgent (e.g., plan for buying a car worth ₹21L).
- Use AssessmentAgent’s report to determine safe limits for downpayment, EMI, and impact on net worth.
- Run multiple financial simulations (e.g., 12/24/36/60-month EMI models).
- Present EMI plans, monthly burden estimates, timeline of impact, and fallback plans.

Key Features:
--------------
- EMI planner with variable interest rates and tenures.
- Downpayment optimization strategy.
- Asset rebalancing suggestion (if funds needed).
- Detect possible clashes with other goals (e.g. buying vs investing).
- Dynamic recalculation based on real-time inputs or intent changes.

Tools/Libs Used:
----------------
- NumPy for EMI & amortization logic.
- matplotlib (optional) for visualization of plan timelines.
- tabulate or JSON formatting for plan outputs.
- Decision-tree-based fallback planner.
"""
from loguru import logger
from src.services.gemini_service import askplan
from src.schemas.plan import PlanResponse, PlanMetadata, GoalMetadata
from src.agents.response_agent import AgentResponse
from src.utils.web_search import fetch_perplexity_planning_insight

from typing import Optional, List

class PlanningAgent:
    def __call__(self, prompt: str, user_id: str, required_data_keys: Optional[List[str]] = None):
        return self.run(prompt, user_id, required_data_keys or [])
    def __init__(self):
        self.logger = logger.bind(agent="PlanningAgent")

    def run(self, prompt: str, user_id: str, required_data_keys: Optional[List[str]] = None):
        """
        Generate a financial plan for the user based on the prompt.
        Uses Gemini-based AI to create general planning suggestions.
        """
        financials = self.fetch_user_financials(user_id)

        goals = self.extract_multiple_goals(prompt, financials, user_id)
        structured_prompt = (
            "You are a strategic financial planning assistant.\n\n"
            "User has described one or more financial goals. Based on their full financial profile, respond with a structured strategy including:\n"
            "1. Goal Summary & Timeline\n"
            "2. Investment or Savings Readiness\n"
            "3. Monthly Affordability & Debt Impact\n"
            "4. Roadmap or EMI Breakdown (if applicable)\n"
            "5. Risk Factors or Clashes\n"
            "6. Personalized Recommendations\n\n"
            "Format as markdown with bold highlights on key amounts (₹), interest rates (%), or durations.\n\n"
            "User's Financial Goals:\n"
        )
        for goal in goals:
            structured_prompt += (
                f"- **Goal Type**: {goal.get('goal_type', 'N/A')}, "
                f"**Amount**: ₹{goal.get('amount', 'N/A')}, "
                f"**Timeline**: {goal.get('timeline_months', 'N/A')} months\n"
            )
        structured_prompt += "\n" + prompt.strip()

        # [Safety Note] This agent is purposefully restricted to use only Perplexity for external advice. Do NOT use Reddit or other forums here.
        # Inject Perplexity insight for future/investment-related prompts
        if any(word in prompt.lower() for word in ["investment", "stock", "mutual fund", "sip", "retirement", "future"]):
            try:
                ppx_advice = fetch_perplexity_planning_insight(prompt)
                structured_prompt += f"\n\n### Community Advice:\n{ppx_advice.strip()}"
            except Exception as e:
                self.logger.warning(f"[PlanningAgent] Failed to fetch Perplexity insight: {e}")

        try:
            ai_response = askplan(structured_prompt, financials)
            risk_notes = [self.analyze_risk(goal, financials) for goal in goals]
            return AgentResponse(
                response=ai_response.get("text") if isinstance(ai_response, dict) else str(ai_response),
                metadata={
                    "agent": "planning",
                    "context_used": True,
                    "goal": [GoalMetadata(**goal).dict() for goal in goals],
                    "risk_analysis": ", ".join(risk_notes)
                }
            )
        except Exception as e:
            self.logger.error(f"[PlanningAgent] AI planning failed: {e}")
            return AgentResponse(
                response="Sorry, I couldn’t generate a planning strategy at the moment.",
                metadata={"agent": "planning"}
            )

    def fetch_user_financials(self, user_id: str) -> dict:
        from src.agent_orchestrator import AgentDataOrchestrator
        orchestrator = AgentDataOrchestrator()
        data = orchestrator.fetch_all_financial_data(user_id)

        def normalize_summary(data_item):
            if isinstance(data_item, list):
                return data_item[0] if data_item and isinstance(data_item[0], dict) else {}
            return data_item if isinstance(data_item, dict) else {}

        net_summary = data.get("networth_summary", {})
        networth_raw = {}
        if isinstance(net_summary, dict):
            if "summary" in net_summary:
                summary_val = net_summary["summary"]
                if isinstance(summary_val, list):
                    networth_raw = summary_val[0] if summary_val else {}
                elif isinstance(summary_val, dict):
                    networth_raw = summary_val
            else:
                networth_raw = net_summary

        bank_data = normalize_summary(data.get("bank_summary", {}).get("summary", {}))
        credit_data = normalize_summary(data.get("credit_summary", {}).get("summary", {}))
        mf_data = normalize_summary(data.get("mf_summary", {}).get("summary", {}))
        epf_data = normalize_summary(data.get("epf_summary", {}).get("summary", {}))
        stock_data = normalize_summary(data.get("stock", {}))

        monthly = data.get("monthly", [])
        income = data.get("income", 0)
        savings = data.get("savings", 0)
        debt = data.get("debt", 0)
        expenses = data.get("expenses", 0)
        incomeTrend = data.get("incomeTrend", [])
        snapshot = data.get("snapshot", {})

        return {
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
            "snapshot": snapshot
        }

    def calculate_emi(self, principal: float, rate: float, months: int) -> float:
        monthly_rate = rate / 12 / 100
        return principal * monthly_rate * ((1 + monthly_rate)**months) / (((1 + monthly_rate)**months) - 1)

    def analyze_risk(self, goal: dict, financials: dict) -> str:
        # Compare EMI with monthly income, existing credit etc.
        return "Low Risk" if goal["amount"] < financials.get("net_worth", 0) * 0.5 else "Moderate Risk"

    def extract_goal_details(self, prompt: str) -> dict:
        import re
        goal = {}
        match = re.search(r'(?i)(wedding|car|trip|home)', prompt)
        if match:
            goal["goal_type"] = match.group(1).lower()
        amt_match = re.search(r'₹?\s?(\d+(?:,\d{3})*(?:\.\d+)?)', prompt)
        if amt_match:
            goal["amount"] = float(amt_match.group(1).replace(',', ''))
        timeline_match = re.search(r'(\d+)\s*(months|month)', prompt, re.IGNORECASE)
        if timeline_match:
            goal["timeline_months"] = int(timeline_match.group(1))
        if "amount" not in goal:
            goal["amount"] = 0
        if "timeline_months" not in goal:
            goal["timeline_months"] = 0
        return goal

    def extract_multiple_goals(self, prompt: str, financials: dict, user_id: str) -> list[dict]:
        import re
        goals = []
        matches = re.findall(r'(wedding|car|bike|trip|home|appliances|apartment|vacation|retirement|investment|stocks|mutual fund)', prompt, re.IGNORECASE)
        for match in matches:
            gtype = match.lower()
            goal = {"goal_type": gtype}
            if gtype in ['stocks', 'mutual fund']:
                portfolio = financials.get('stock' if gtype == 'stocks' else 'mf', {})
                if portfolio:
                    goal['correlation_info'] = f"{gtype.title()} holdings found and considered for planning."
                else:
                    goal['correlation_info'] = f"No existing {gtype} investments found. Suggesting new opportunities."
            amt_match = re.search(rf'{gtype}.*?₹?\s?(\d+(?:,\d{{3}})*(?:\.\d+)?)', prompt, re.IGNORECASE)
            if amt_match:
                goal["amount"] = float(amt_match.group(1).replace(',', ''))
            else:
                goal["amount"] = 0
            time_match = re.search(rf'{gtype}.*?(\d+)\s*(months|month)', prompt, re.IGNORECASE)
            if time_match:
                goal["timeline_months"] = int(time_match.group(1))
            else:
                goal["timeline_months"] = 12
            goals.append(goal)

        # Add goals from memory tagged as "wedding"
        try:
            from src.services.memory_store import fetch_goals_by_tag
            wedding_goals = fetch_goals_by_tag(user_id=user_id, tag="wedding")
            for mem_goal in wedding_goals:
                if mem_goal not in goals:
                    goals.append(mem_goal)
        except Exception:
            pass

        return goals or [{"goal_type": "general", "amount": 0, "timeline_months": 12}]