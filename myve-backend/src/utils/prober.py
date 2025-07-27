import json
import os

USER_PROGRESS_FILE = "user_probing_progress.json"

def load_user_progress():
    if os.path.exists(USER_PROGRESS_FILE):
        with open(USER_PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_progress(progress):
    with open(USER_PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def get_user_step(user_id, intent):
    progress = load_user_progress()
    return progress.get(user_id, {}).get(intent, 1)

def update_user_step(user_id, intent, step):
    progress = load_user_progress()
    if user_id not in progress:
        progress[user_id] = {}
    progress[user_id][intent] = step
    save_user_progress(progress)

PROBING_SEQUENCES = {
    "buy_bike": {
        "step_1": "When do you plan to buy the bike?",
        "step_2": "Do you intend to pay in full or via EMI?",
        "step_3": "Will this purchase impact your savings goal?"
    },
    "buy_house": {
        "step_1": "Are you looking for a self-occupied or rental property?",
        "step_2": "What is your preferred budget range?",
        "step_3": "Do you already have a loan or down payment plan in mind?"
    },
    "buy_laptop": {
        "step_1": "Is this laptop for work, study, or entertainment?",
        "step_2": "What's your budget range?",
        "step_3": "Do you plan to purchase it outright or through EMI?"
    },
    "buy_appliance": {
        "step_1": "Which home appliance are you considering?",
        "step_2": "Do you want it for immediate use or a future need?",
        "step_3": "Are you considering cash or installment payment?"
    }
}

def get_probing_question(intent, step):
    """
    Retrieve the probing question for a given intent and step.
    """
    return PROBING_SEQUENCES.get(intent, {}).get(f"step_{step}", None)

def get_all_probing_questions(intent):
    """
    Get all probing questions in sequence for an intent.
    """
    sequence = PROBING_SEQUENCES.get(intent, {})
    return [sequence[key] for key in sorted(sequence.keys())]


# Dynamically fetch the next probing question for the given user and intent.
def get_next_probing_question(user_id, intent):
    """
    Dynamically fetch the next probing question for the given user and intent.
    Returns None if no more steps remain.
    """
    step = get_user_step(user_id, intent)
    question = get_probing_question(intent, step)
    if question:
        update_user_step(user_id, intent, step + 1)
    return question
