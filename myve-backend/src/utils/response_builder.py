from src.utils import response_builder

def build_financial_advice_response(user_input, financial_context, probing_answers=None):
    """
    Build a curated, human-like financial advisor response.
    
    Parameters:
        - user_input: Original query from the user.
        - financial_context: Dictionary or string summary of user financial data.
        - probing_answers: Optional dictionary of follow-up answers if probing occurred.
    
    Returns:
        - A natural language response combining insights and recommendations.
    """

    base = f"Hello there! I'm Myve AI, your personal financial adviser.\n\n"

    base += f"You're asking: \"{user_input}\"\n\n"

    base += "Here's what I found based on your financial situation:\n"
    if isinstance(financial_context, dict):
        base += f"- **Goal:** {financial_context.get('goal', 'General')}\n"
        base += f"- **Generated On:** {financial_context.get('generated_on', 'N/A')}\n\n"
    else:
        base += f"{financial_context}\n\n"

    if probing_answers:
        base += "Thanks for sharing more information. Here’s what I understood additionally:\n"
        for key, val in probing_answers.items():
            base += f"- **{key.replace('_', ' ').capitalize()}**: {val}\n"
        base += "\nThese help me better personalize your advice based on your goals and preferences.\n\n"

    base += "My financial recommendation:\n\n"

    if isinstance(financial_context, dict) and "steps" in financial_context:
        context = financial_context.get("user_context", {})
        for idx, step in enumerate(financial_context["steps"], 1):
            task = step.get("task", "Do something important")
            detail = step.get("details", "")
            base += f"{idx}. **{task}** – {detail}\n"
        if financial_context.get("goal") == "buy_bike" and context.get("surplus", 0) == 0:
            base += "→ Right now, this might stretch your finances. Let’s fix the overdues first — then we’ll ride!\n"
    else:
        if isinstance(financial_context, dict):
            context = financial_context.get("user_context", {})
            if financial_context.get("goal") == "buy_bike" and context.get("surplus", 0) == 0:
                base += "→ Right now, this might stretch your finances. Let’s fix the overdues first — then we’ll ride!\n"
            else:
                base += "→ Based on the data, I suggest addressing your current debts before making new purchases. Paying upfront may be better than taking on high-interest EMI in your case.\n"

    base += "\nIf you need help planning payments, setting goals, or comparing offers, just let me know!"

    return base