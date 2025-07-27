def detect_prompt_type(user_input):
    """
    Classifies the user's prompt into:
    - 'type': 'decision' or 'direct'
    - 'intent': Specific high-level intent (e.g., 'buy_bike', 'buy_house')
    """

    keyword_intents = {
        "buy_bike": [
            "buy a bike", "purchase a bike", "planning to buy a bike", "should i buy a bike",
            "want to buy a bike"
        ],
        "buy_laptop": [
            "buy a laptop", "purchase a laptop", "planning to buy a laptop", "should i buy a laptop"
        ],
        "buy_house": [
            "buy a house", "purchase a house", "planning to buy a house", "should i buy a house"
        ],
        "plan_investment": [
            "invest in", "safe to invest", "time to invest", "worth investing", "should i invest"
        ],
        "buy_car": [
            "buy a car", "purchase a car", "planning to buy a car", "should i buy a car", "looking to buy a car", "is it wise to buy a car"
        ],
    }

    decision_keywords = [
        "can i", "should i", "do you think", "is it wise", "is it okay", 
        "planning to buy", "thinking to buy", "purchase", "invest in", 
        "sell my", "should we", "is this the right time", "could i afford",
        "looking to buy", "worth buying", "is it a good idea", 
        "do you recommend", "safe to invest", "time to invest", 
        "is this affordable", "considering to buy", "thinking of purchasing",
        "worth investing", "worth selling", "should i sell", "plan to purchase",
        "how safe is it", "how risky is it", "planning for emi", 
        "should i pay in full", "choose emi or full", "should i wait to buy"
    ]

    lower_input = user_input.lower()
    prompt_type = "direct"
    intent = "general"

    for keyword in decision_keywords:
        if keyword in lower_input:
            prompt_type = "decision"
            break

    for intent_label, keywords in keyword_intents.items():
        for phrase in keywords:
            if phrase in lower_input:
                intent = intent_label
                break

    return {"type": prompt_type, "intent": intent}