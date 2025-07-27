import datetime

def build_action_plan(intent, responses, user_context):
    """
    Builds a simple multi-step action plan based on user goal (intent),
    their answers to probing questions, and current financial context.
    Acts as a fallback when LLM fails to return a valid structured plan.

    :param intent: str, user goal like "buy_home", "retire_early", "reduce_debt"
    :param responses: dict, answers to probing questions
    :param user_context: dict, includes income, expenses, assets, liabilities, etc.
    :return: dict, structured action plan
    """

    plan = {
        "goal": intent,
        "generated_on": str(datetime.date.today()),
        "steps": []
    }

    # Fallback guard: if only surplus is known, treat it as income with zero expenses
    if user_context.get("income", 0) == 0 and user_context.get("expenses", 0) == 0 and user_context.get("surplus"):
        user_context["income"] = user_context["surplus"]
        user_context["expenses"] = 0

    income = user_context.get("income", 0)
    expenses = user_context.get("expenses", 0)
    surplus = income - expenses
    debt = user_context.get("total_debt", 0)
    savings = user_context.get("total_savings", 0)

    overdue_amount = user_context.get("overdue_amount", 0)

    if intent == "buy_home":
        target_amount = responses.get("target_cost", 0)
        time_frame = responses.get("time_frame", 5)

        plan["steps"].append({
            "task": "Start a dedicated down payment savings plan",
            "details": f"Save ₹{int(target_amount * 0.2)} as down payment over {time_frame} years."
        })
        plan["steps"].append({
            "task": "Review EMI affordability",
            "details": f"Ensure EMI does not exceed 35% of your net monthly income (₹{int(income * 0.35)})."
        })
        plan["steps"].append({
            "task": "Check credit score eligibility",
            "details": "Ensure score > 700 to qualify for better interest rates."
        })

    elif intent == "buy_car":
        plan["steps"].append({
            "task": "Pay off overdue credit accounts",
            "details": f"You currently have ₹{overdue_amount} overdue. Clear these first to improve your credit score and avoid high-interest loans."
        })
        plan["steps"].append({
            "task": "Decide car budget",
            "details": f"With a monthly surplus of ₹{surplus}, you can target a car within ₹{surplus * 12 * 2} over 2 years. Adjust if planning EMI."
        })
        plan["steps"].append({
            "task": "Compare loan options and pre-approvals",
            "details": "Check banks/NBFCs for car loan interest rates. Consider total interest cost before signing up."
        })
        plan["steps"].append({
            "task": "Plan for fuel, insurance, and servicing",
            "details": "Include ₹3000–₹5000/month in your budget for post-purchase running costs."
        })

    elif intent == "buy_bike":
        overdue = user_context.get("overdue_amount", 0)
        total_debt = user_context.get("total_debt", 0)
        surplus = user_context.get("surplus", 0)

        plan["steps"].append({
            "task": "Handle existing overdues and EMIs",
            "details": f"Your current debt is ₹{total_debt} and overdue is ₹{overdue}. Clear these before taking on a new bike EMI."
        })
        plan["steps"].append({
            "task": "Estimate affordable bike range",
            "details": f"With ₹{surplus} monthly surplus, a safe budget is around ₹{max(surplus * 12, 0)}. Avoid stretching beyond this to prevent financial stress."
        })
        plan["steps"].append({
            "task": "Choose model and explore offers",
            "details": "Look for festive discounts, zero down payment schemes, and insurance bundles."
        })

    elif intent == "buy_laptop":
        plan["steps"].append({
            "task": "Plan purchase from surplus income",
            "details": f"Allocate a portion of your ₹{surplus} monthly surplus. Consider 0% EMI or short-term savings."
        })
        plan["steps"].append({
            "task": "Explore education or digital upgrade offers",
            "details": "If for work or study, check for offers, student discounts, or company reimbursements."
        })

    elif intent == "plan_vacation":
        budget = responses.get("target_cost", 0)
        plan["steps"].append({
            "task": "Start short-term travel fund",
            "details": f"Save ₹{int(budget / 6)} monthly to reach your travel goal in 6 months."
        })
        plan["steps"].append({
            "task": "Avoid using credit for travel",
            "details": "Do not take loans for leisure trips. Use surplus or planned savings only."
        })

    elif intent == "home_loan":
        plan["steps"].append({
            "task": "Review loan eligibility",
            "details": f"Your monthly income is ₹{income}. Aim for EMI under ₹{int(income * 0.4)}. Ensure credit score >700."
        })
        plan["steps"].append({
            "task": "Prepare for down payment",
            "details": "Save at least 20% of home cost (₹X). Avoid exhausting all your savings."
        })
        plan["steps"].append({
            "task": "Factor in other home costs",
            "details": "Budget for registration, interior work, stamp duty, and emergency fund."
        })

    elif intent == "reduce_debt":
        plan["steps"].append({
            "task": "List all active loans",
            "details": f"Total debt is ₹{debt}. Prioritize loans with high interest."
        })
        plan["steps"].append({
            "task": "Create monthly debt repayment plan",
            "details": f"Use your monthly surplus of ₹{surplus} to aggressively pay off debt."
        })

    elif intent == "retire_early":
        target_age = responses.get("target_age", 50)
        current_age = responses.get("current_age", 30)
        years_left = target_age - current_age
        monthly_goal = (responses.get("target_corpus", 0) - savings) / (years_left * 12)

        plan["steps"].append({
            "task": "Set up recurring investments",
            "details": f"Invest ₹{int(monthly_goal)} per month to reach your target corpus."
        })
        plan["steps"].append({
            "task": "Review portfolio allocation",
            "details": "Balance between equity, debt, and alternative assets based on your risk profile."
        })

    else:
        plan["steps"].append({
            "task": "Gather more information",
            "details": "Your goal needs more clarity. Please answer a few more questions."
        })

    plan["user_context"] = user_context
    return plan

def is_valid_plan(plan):
    """
    Validates if the input plan from Gemini is structured correctly.
    Expects a dict with 'goal', 'generated_on', and non-empty 'steps'.
    """
    return isinstance(plan, dict) and "goal" in plan and "generated_on" in plan and "steps" in plan and isinstance(plan["steps"], list) and len(plan["steps"]) > 0