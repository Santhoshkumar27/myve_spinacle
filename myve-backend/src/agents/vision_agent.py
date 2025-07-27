import subprocess
from src.services.memory_store import save_final_advice_log
import os
import json
from datetime import datetime
from src.agents.response_agent import ResponseAgent

class VisionAgent:
    def __init__(self):
        self.response_agent = ResponseAgent()

    def run(self, prompt: str, user_id: str, is_triggered_by_ui: bool = False):
        # Prepend vision flag for skip-cache logic in ResponseAgent
        formatted_prompt = (
            "[vision] You are a financial agent analyzing visual screen content.\n\n"
            "The extracted OCR contains:\n"
            f"{prompt.strip()}\n\n"
            "Your task is to produce a detailed, multi-section financial breakdown:\n"
            "1. Financial Readiness\n"
            "2. Purchase Affordability\n"
            "3. Planning or Budgeting Guidance\n"
            "4. Loan/Repayment Tips if needed\n"
            "5. Booking or Offer Strategy\n"
            "6. Overall Summary & Encouragement\n\n"
            "Respond with practical, well-structured points, bold figures, and clear formatting. Avoid vague responses."
        )
        schema = self.response_agent.interpret_user_goal(prompt.strip())
        result = self.response_agent.route_with_schema(prompt.strip(), user_id=user_id, schema_override=schema)

        # If result is already a formatted response string (fallback), return directly
        if isinstance(result, str):
            return result

        # If result has no structured response, return default
        if not hasattr(result, "response") or not result.response.strip():
            return "Sorry, we couldn’t extract any useful financial insight from this screen. Please try with a more finance-relevant view."

        # Format natural language response
        natural_response = self.response_agent.format_natural_response(result)

        # Extract metadata
        detected_intents = []
        category = None
        agents_triggered = []
        if hasattr(result, "metadata") and isinstance(result.metadata, dict):
            detected_intents = result.metadata.get("intents", [])
            category = result.metadata.get("category", None)
            agents_triggered = result.metadata.get("agents", [])

        # Log vision interaction
        log_entry = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "ocr_text": prompt.strip(),
            "detected_intents": detected_intents,
            "category": category,
            "agents_triggered": agents_triggered,
            "final_advice": natural_response.strip(),
            "is_triggered_by_ui": is_triggered_by_ui
        }

        os.makedirs("sessions", exist_ok=True)
        history_path = f"sessions/vision_history_{user_id}.jsonl"
        with open(history_path, "a") as log_file:
            log_file.write(json.dumps(log_entry) + "\n")

        # Save final summarised advice to memory store
        save_final_advice_log(user_id=user_id, ocr_text=prompt.strip(), advice=natural_response.strip(), metadata={
            "intents": detected_intents,
            "category": category,
            "agents_triggered": agents_triggered,
            "is_triggered_by_ui": is_triggered_by_ui
        })

        return natural_response

    def start_electron_app(self, user_id: str):
        import logging
        try:
            logging.info(f"🚀 Launching Electron app for user: {user_id}")
            process = subprocess.Popen(
                f"npm run start-vision -- --user={user_id}",
                cwd="/Users/santhoshkumar/Documents/myve/myve-vision-electron",
                shell=True,
                executable="/bin/bash"
            )
            pid_file = "/tmp/vision_electron_pid.txt"
            with open(pid_file, "w") as f:
                f.write(str(process.pid))
            logging.info(f"✅ Electron app launched with PID {process.pid}")
            return {"status": "Electron app started", "pid": process.pid}
        except Exception as e:
            logging.error(f"❌ Failed to launch Electron app: {e}")
            return {"error": str(e)}

    def stop_electron_app(self):
        import logging
        try:
            pid_file = "/tmp/vision_electron_pid.txt"
            if os.path.exists(pid_file):
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())
                os.remove(pid_file)
                os.kill(pid, 15)  # Send SIGTERM
                logging.info(f"✅ Electron app with PID {pid} stopped successfully.")
                return {"status": f"Electron app with PID {pid} stopped"}
            else:
                logging.warning("⚠️ No PID file found; nothing to stop.")
                return {"status": "No running Electron app found"}
        except Exception as e:
            logging.error(f"❌ Failed to stop Electron app: {e}")
            return {"error": str(e)}