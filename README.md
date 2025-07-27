# Myve Backend

This is the backend service powering the **Myve Financial Intelligence System**, a modular agentic AI engine for financial planning, simulation, and reporting.

## 🔧 Tech Stack

- **Python 3.11+**
- **Flask** for API routing
- **MongoDB** for session and message persistence
- **Gemini & Perplexity APIs** for LLM-driven insights
- **Modular Agents**: Buy, Repay, Plan, Assess, Vision, Data, Presentation
- **Google Cloud Vision API** for OCR

## 📁 Key Directory Structure

```
myve-backend/
├── src/
│   ├── agents/               # Core AI agents (response, planning, data, etc.)
│   ├── models/               # MongoDB models for sessions and messages
│   ├── routes/               # Flask route blueprints (e.g., ai_route.py)
│   ├── services/             # LLM, OCR, and supporting service wrappers
│   ├── utils/                # Utility modules like prober, classifier, etc.
│   └── app.py                # Main Flask app entrypoint
```

## 🧠 Available Agents

- `ResponseAgent` – Main router for all LLM tasks and prompt classification
- `BuyingAgent`, `RepayingAgent`, `PlanningAgent`, `AssessmentAgent` – Specialized financial domain agents
- `VisionAgent` – Handles image-based financial analysis
- `DataAgent` – Generates simulations, savings plans, etc. based on raw data
- `DataPresentationAgent` – Formats data into insights, cards, and timelines

## 🚀 API Endpoints (Selected)

- `POST /api/ai/ask` – Route natural queries to appropriate agent
- `POST /api/ai/interpret` – Returns goal schema (agents, intent, urgency)
- `POST /api/ai/suggest` – Suggests follow-up queries
- `POST /api/ai/data_agent/simulate` – Simulate a financial goal (savings, repayment, etc.)
- `POST /api/ai/data_agent/timeline` – Returns user's financial timeline
- `POST /api/ai/data_agent/cards` – Generates summary cards from data

## 📦 Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/spinacle/myve-backend.git
   cd myve-backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables (use `.env`):
   - `GEMINI_API_KEY=your_key_here`
   - `MONGO_URI=your_mongo_uri`
   - `GOOGLE_APPLICATION_CREDENTIALS=path_to_your_gcloud_json`

5. Run the Flask app:
   ```bash
   python src/app.py
   ```

## 🧪 Testing

The backend logs activity using `logging` and shows per-agent debug trails. Use tools like Postman or the React frontend at `myve-app/` to test workflows.

## 🧩 Notes

- VisionAgent integrates tightly with Electron via `/vision/control`.
- This codebase is optimized for agentic flexibility and context awareness.
- Designed to plug into modular frontend pages like Timeline, Data Simulator, and Chat.

---

Built by [Spinacle](https://spinacle.net)