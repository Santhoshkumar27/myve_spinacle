import logging
from typing import Dict
from src.agents.assessment_agent import AssessmentAgent
from src.services.gemini_service import call_gemini, askbuy
from src.utils.web_search import fetch_product_insights, fetch_realworld_buying_info, render_product_summary  # hypothetical utility to search prices
from src.schemas.buy import CreditSummary, BankSummary  # assumed to exist
from src.agent_orchestrator import AgentDataOrchestrator
from src.schemas.plan_metadata import PlanMetadata, SavingsProjection
from src.agents.response_agent import AgentResponse  # Ensure this is at the top if not already

logger = logging.getLogger(__name__)

class BuyingAgent:
    def __init__(self):
        self.assessment_agent = AssessmentAgent()
        self.logger = logger
        self.orchestrator = AgentDataOrchestrator()

    def run(self, prompt: str, user_id: str, use_assessment: bool = False):
        try:
            # Guard clause for missing user_id
            if user_id == "unknown":
                return AgentResponse(
                    response="We need your mobile number to access financial data and give buying advice. Please log in again or update your ID.",
                    metadata={"agent": "buying", "reason": "missing_user_id", "original_prompt": prompt}
                )
            # Step 1: Assess financial health or fetch all data
            if use_assessment:
                assessment = self.assessment_agent.run(
                    prompt="Summarize user's financial readiness for buying decisions.",
                    user_id=user_id,
                    required_data_keys=["credit", "bank", "networth"]
                )
                credit_score = assessment.get("credit_summary", {}).get("creditScore", "N/A")
                disposable_income = assessment.get("bank_summary", {}).get("averageBalance", 0)
                total_debt = assessment.get("credit_summary", {}).get("totalCurrentBalance", 0)
                networth_summary = assessment.get("networth_summary", {})
                snapshot_summary = {}
            else:
                financials = self.orchestrator.fetch_all_financial_data(user_id)
                credit_summary = financials.get("credit_summary", {})
                self.logger.debug(f"[BuyingAgent] Raw credit_summary: {credit_summary}")
                bank_summary = financials.get("bank_summary", {})
                networth_summary = financials.get("networth_summary", {})
                snapshot_summary = financials.get("snapshot", {}) or financials.get("final_snapshot", {})

                credit_score = (
                    credit_summary.get("creditScore") or
                    credit_summary.get("summary", {}).get("creditScore") or
                    credit_summary.get("summary", {}).get("bureauScore", {}).get("value") or
                    credit_summary.get("score", {}).get("value") or
                    "N/A"
                )
                if isinstance(credit_score, str) and not credit_score.isdigit():
                    credit_score = ''.join(filter(str.isdigit, credit_score))
                if not credit_score or credit_score == "N/A":
                    self.logger.warning(f"[BuyingAgent] Missing or invalid credit score. Detected value: {credit_score}. Skipping buying advice.")
                    return AgentResponse(
                        response="We couldn’t access your credit score to determine your financial readiness for this purchase. Please link your credit account and try again.",
                        metadata={"agent": "buying", "reason": "missing_credit_score", "original_prompt": prompt}
                    )
                disposable_income = bank_summary.get("averageBalance", 0)
                total_debt = credit_summary.get("totalCurrentBalance", 0)

            # Step 2: Interpret what to buy
            schema = call_gemini(f"""
            Classify this buying query and return a JSON:
            - item (extracted object being purchased)
            - category (bike, surgery, gold, house, etc.)
            - purpose (gift, wedding, education)
            - urgency (low/medium/high)

            Query: {prompt}
            """)

            import json
            schema_data = {}
            try:
                schema_data = json.loads(schema)
                item_category = schema_data.get("category", "unknown").lower()
                item_name = schema_data.get("item", "").strip()
                self.logger.info(f"[BuyingAgent] LLM-derived category: {item_category}, item: {item_name}")
            except Exception as e:
                item_category = "unknown"
                item_name = ""

            # Step 3: Get real-world prices and offers
            # Use fetch_realworld_buying_info for real-world product data
            # Pass item_name if available for better specificity, fallback to category
            if item_name:
                product_data = fetch_realworld_buying_info(item_category=item_category, item=item_name, prompt=prompt)
            else:
                product_data = fetch_realworld_buying_info(item_category=item_category, prompt=prompt)
            if not product_data.get("price") or product_data.get("price") == 0:
                self.logger.warning("[BuyingAgent] Product price was 0 — real-world price not found.")
                return AgentResponse(
                    response="We couldn’t find the real-world price for this product. Please try again later or refine your query.",
                    metadata={"agent": "buying", "reason": "missing_price", "original_prompt": prompt}
                )
            if disposable_income is None or disposable_income == 0:
                try:
                    income = float(snapshot_summary.get("income") or 0)
                    expenses = float(snapshot_summary.get("expenses") or 0)
                    if income > 0 and expenses > 0:
                        disposable_income = income - expenses
                        self.logger.info(f"[BuyingAgent] Fallback disposable income calculated: {disposable_income}")
                    else:
                        self.logger.warning("[BuyingAgent] Cannot calculate fallback disposable income due to missing or zero income/expenses.")
                        disposable_income = 0
                except Exception as e:
                    self.logger.error(f"[BuyingAgent] Error computing fallback disposable income: {e}")
                    disposable_income = 0
                    
            # Step 4: Analyze budget fitness
            suggested_budget = 0.3 * disposable_income  # allow 30% of avg. balance for purchase
            try:
                price_value = float(str(product_data.get("price", 1e9)).replace(",", "").replace("₹", "").strip())
            except Exception:
                price_value = 1e9
            # Compute consumption ratio and feedback
            if disposable_income > 0:
                consumption_ratio = price_value / disposable_income
            else:
                consumption_ratio = 0
            consumption_percent = round(consumption_ratio * 100, 2)
            consumption_feedback = f"This purchase will consume {consumption_percent}% of your monthly disposable income"
            if consumption_ratio < 0.3:
                consumption_feedback += " — well within the safe limit."
            elif consumption_ratio < 0.5:
                consumption_feedback += " — moderately safe, consider budgeting."
            else:
                consumption_feedback += " — high impact, ensure financial buffer."
            # Before calling askbuy, check if price is 0 and log
            if price_value == 0:
                self.logger.warning("[BuyingAgent] Product price returned as ₹0 – skipping affordability check.")
                affordability = "❓ Price unavailable"
                can_afford_upfront = False
            else:
                can_afford_upfront = price_value <= suggested_budget
                affordability = "✅ Within budget" if can_afford_upfront else "⚠️ May require EMI"

            # Handle unknown product case
            if item_category in ("unknown", "other", "") and not product_data.get("reddit_threads"):
                return AgentResponse(
                    response="I couldn't determine what you're trying to buy. Could you please rephrase or provide more details?",
                    metadata={"agent": "buying", "reason": "unclear_intent", "original_prompt": prompt}
                )

            # Step 4.5: Plan impact metadata
            plan_metadata = PlanMetadata(
                impact_on_networth="Minor reduction due to this purchase" if can_afford_upfront else "Significant if EMI extends beyond 6 months",
                savings_projection=SavingsProjection(
                    current_monthly_savings=disposable_income,
                    projected_savings_post_purchase=(disposable_income * 6 - price_value) if can_afford_upfront else (disposable_income * 6 - 0.2 * price_value),
                    months_to_recover=3 if not can_afford_upfront else 0,
                    alert="Ensure buffer is maintained for next 3 months" if not can_afford_upfront else None
                ),
                investment_shift="No change" if can_afford_upfront else "Consider pausing one SIP to manage EMI load"
            )

            # Tag goal_category for purpose-based planning
            if schema_data.get("purpose") in ("wedding", "education", "surgery"):
                plan_metadata.goal_category = schema_data.get("purpose", "")
            elif schema_data.get("category") in ("surgery", "travel", "retirement", "appliances"):
                plan_metadata.goal_category = schema_data.get("category", "")

            # Step 5: Structured Response Construction
            response_sections = []

            # Section 1: Financial Overview
            financial_overview = f"""**💼 Financial Snapshot**
- **Credit Score:** {credit_score}
- **Monthly Disposable Income:** ₹{int(disposable_income):,}
- **Current Debt:** ₹{int(total_debt):,}
"""
            response_sections.append(financial_overview)

            # Section 2: Product Analysis
            product_analysis = f"""**📦 Product Insight**
- **Item:** {item_name if item_name else item_category.title()}
- **Estimated Price:** ₹{price_value:,.0f}
- **Affordability:** {affordability}
- {consumption_feedback}
"""
            if product_data.get("source"):
                product_analysis += f"- **Source:** {product_data['source']}"
            response_sections.append(product_analysis)

            # Section 3: Net Worth Impact
            networth_info = ""
            if networth_summary.get("totalNetWorth", {}).get("raw"):
                net_before = networth_summary["totalNetWorth"]["raw"]
                net_after = net_before - price_value
                net_change = ((net_after - net_before) / net_before) * 100
                networth_info = f"""**📉 Net Worth Impact**
- Net Worth Before: ₹{net_before:,.0f}
- After Purchase: ₹{net_after:,.0f}
- Change: {net_change:.1f}%
- Comment: {plan_metadata.impact_on_networth}
- Recovery Estimate: {plan_metadata.savings_projection.months_to_recover} months
"""
                response_sections.append(networth_info)

            # Section 4: Context Summary
            if snapshot_summary:
                summary_parts = []
                if "income" in snapshot_summary:
                    summary_parts.append(f"Income: ₹{int(snapshot_summary['income']):,}")
                if "expenses" in snapshot_summary:
                    summary_parts.append(f"Expenses: ₹{int(snapshot_summary['expenses']):,}")
                if "savings" in snapshot_summary:
                    summary_parts.append(f"Savings: ₹{int(snapshot_summary['savings']):,}")
                if summary_parts:
                    response_sections.append("**📊 Financial Context**\n- " + "\n- ".join(summary_parts))

            # Section 5: Product Summary and Gemini Tips
            response_sections.append("**🔍 Product Summary**\n" + render_product_summary(product_data))

            buying_data = {
                "credit_score": credit_score,
                "disposable_income": disposable_income,
                "current_debt": total_debt,
                "item": item_name if item_name else item_category,
                "price": price_value,
                "can_afford_upfront": can_afford_upfront,
                "networth_before": networth_summary.get("totalNetWorth", {}).get("raw", 0),
                "networth_after": networth_summary.get("totalNetWorth", {}).get("raw", 0) - price_value,
                "snapshot": snapshot_summary
            }

            try:
                buying_insight = askbuy(prompt, buying_data)
            except Exception as e:
                self.logger.error(f"[askbuy] Error generating buying advice: {e}")
                buying_insight = {"text": "Gemini failed to generate advice."}
            if isinstance(buying_insight, dict) and buying_insight.get("text"):
                gemini_lines = buying_insight["text"].strip().splitlines()
                if not gemini_lines:
                    first_line = ""
                    highlights = buying_insight["text"]
                else:
                    first_line = gemini_lines[0][:200]  # truncate first line if long
                    highlights = "\n".join([f"- {line[:180]}" for line in gemini_lines[1:4] if line.strip()])
                response_sections.append(f"**🤖 Gemini Tips**\n{first_line}\n{highlights}")

            # Section 6: Category-specific tips
            if item_category == "gold":
                response_sections.append("**🪙 Gold-Specific Tips**\n- Opt for BIS Hallmark and HUID-encoded pieces.\n- For coins/bars, check for GST exemptions.")

            # Final formatted response
            response = "\n\n".join(response_sections)

            # Validation: Ensure key financial data is present before returning advice
            if disposable_income <= 0:
                self.logger.warning(f"[BuyingAgent] Missing disposable income. Cannot provide accurate buying advice.")
                return AgentResponse(
                    response="We couldn’t access your disposable income to determine if this purchase is suitable. Please link your bank account and try again.",
                    metadata={"agent": "buying", "reason": "missing_income", "original_prompt": prompt}
                )

            # Log purchase decision to memory store (with fallback if not present)
            try:
                try:
                    from src.services.memory_store import save_purchase_log
                except ModuleNotFoundError:
                    def save_purchase_log(*args, **kwargs):
                        import logging
                        logging.warning("[Fallback] memory_store not found. Purchase log skipped.")
                save_purchase_log(user_id=user_id, item=item_name, amount=price_value, plan=plan_metadata.dict())
            except Exception as e:
                self.logger.warning(f"[BuyingAgent] Failed to log purchase decision: {e}")

            self.logger.info(f"[BuyingAgent] Returning response for item: {item_category} with price: {price_value} from source: {product_data.get('source')}")
            # Always return AgentResponse as final return
            return AgentResponse(
                response=response,
                metadata={
                    "agent": "buying",
                    "item": item_category,
                    "price": price_value,
                    "source": product_data.get("source", ""),
                    "can_afford_upfront": can_afford_upfront,
                    "plan": plan_metadata.dict(),
                    "snapshot": snapshot_summary,
                    "networth": networth_summary
                }
            )
        except Exception as e:
            self.logger.exception(f"[BuyingAgent] Error: {e}")
            return AgentResponse(
                response="I couldn't assist with this purchase right now. Please try again later.",
                metadata={"agent": "buying", "error": str(e)}
            )

    def __call__(self, prompt: str, user_id: str, required_data_keys: list[str] = None):
        return self.run(prompt, user_id)
