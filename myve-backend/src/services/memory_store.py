


import os
import json
from datetime import datetime

def save_vision_log(user_id: str, log: dict, directory: str = "sessions"):
    os.makedirs(directory, exist_ok=True)
    filename = f"{directory}/vision_history_{user_id}.jsonl"
    log["timestamp"] = datetime.utcnow().isoformat()
    with open(filename, "a") as f:
        f.write(json.dumps(log) + "\n")


# Save purchase log for a user
def save_purchase_log(user_id: str, item: str, amount: float, plan: dict, directory: str = "sessions"):
    os.makedirs(directory, exist_ok=True)
    filename = f"{directory}/purchase_log_{user_id}.jsonl"
    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "item": item,
        "amount": amount,
        "plan": plan
    }
    with open(filename, "a") as f:
        f.write(json.dumps(log) + "\n")


# Save final summarised financial advice
def save_final_advice_log(user_id: str, ocr_text: str, advice: str, metadata: dict = None, directory: str = "sessions"):
    os.makedirs(directory, exist_ok=True)
    filename = f"{directory}/final_advice_log_{user_id}.jsonl"
    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "ocr_text": ocr_text,
        "advice": advice,
        "metadata": metadata or {}
    }
    with open(filename, "a") as f:
        f.write(json.dumps(log) + "\n")