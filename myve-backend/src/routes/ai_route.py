from src.models.sessions import sessions_collection
from src.models.messages import messages_collection
import uuid
import datetime
from flask import Blueprint, request, jsonify, session
from src.services.gemini_service import ask_gemini, suggest_next_queries

from src.utils.intent_classifier import detect_prompt_type
from src.utils.prober import get_all_probing_questions
import asyncio

from src.agents.response_agent import ResponseAgent

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


# New /interpret route (before /ask)
@ai_bp.route("/interpret", methods=["POST"])
def interpret():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        user_id = session.get("mobile_number", "anonymous")
        from src.agents.response_agent import ResponseAgent
        agent = ResponseAgent()
        schema = agent.interpret_user_goal(prompt)
        return jsonify({
            "agents": schema.get("agents", []),
            "intents": schema.get("intents", []),
            "item": schema.get("item", ""),
            "category": schema.get("category", ""),
            "urgency": schema.get("urgency", "")
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@ai_bp.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        probing_answers = data.get("probingAnswers", [])
        session_id = data.get("session_id", None)
        user_id = session.get("mobile_number", "anonymous")

        from src.agents.response_agent import ResponseAgent
        agent = ResponseAgent()
        result = agent.route(prompt, user_id)
        if not result or not getattr(result, "response", None):
            return jsonify({"error": "No valid response returned by agent", "response": ""}), 500

        # Attach session ID to response if missing
        if not session_id:
            session_id = str(uuid.uuid4())
            session["active_session_id"] = session_id
            sessions_collection.insert_one({
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.datetime.utcnow(),
                "title": prompt[:40] + "..." if len(prompt) > 40 else prompt
            })

        messages_collection.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "sender": "user",
            "text": prompt,
            "timestamp": datetime.datetime.utcnow()
        })

        messages_collection.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "sender": "bot",
            "text": result.response,
            "timestamp": datetime.datetime.utcnow()
        })

        # Updated response_payload: include agents and intents from result.metadata
        response_payload = {
            "response": result.response,
            "session_id": session_id,
            "agents": result.metadata.get("agents", []) if hasattr(result, "metadata") and isinstance(result.metadata, dict) else [],
            "intents": result.metadata.get("intents", []) if hasattr(result, "metadata") and isinstance(result.metadata, dict) else [],
        }

        import json

        def safe_json(obj):
            try:
                return json.loads(json.dumps(obj, default=str))
            except Exception:
                return str(obj)

        if result.metadata:
            flat_metadata = {}
            for key, meta in result.metadata.items():
                if isinstance(meta, dict):
                    flat_metadata.update(meta)
            response_payload["metadata"] = safe_json(flat_metadata)
            if "graphs" in flat_metadata:
                response_payload["graphs"] = flat_metadata["graphs"]
            if "graph_points" in flat_metadata:
                response_payload["graph_points"] = flat_metadata["graph_points"]
            # (agents and intents already added above)

        if hasattr(result, "plans"):
            response_payload["plans"] = safe_json(result.plans)

        return jsonify(response_payload)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "response": "Something went wrong while processing your request."}), 500

# New route to suggest next queries
@ai_bp.route("/suggest", methods=["POST"])
def suggest():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        response_text = data.get("response", "")

        suggestions = asyncio.run(suggest_next_queries(prompt, response_text))
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"suggestions": [], "error": str(e)}), 500


# New route to fetch stored context data
@ai_bp.route("/fetch_context_data", methods=["GET"])
def fetch_context_data():
    context_data = session.get("context_data", {})
    return jsonify(context_data)


# Route to fetch all sessions for the current user
@ai_bp.route("/sessions", methods=["GET"])
def list_sessions():
    mobile = session.get("mobile_number", "anonymous")
    sessions = list(sessions_collection.find({"user_id": mobile}).sort("created_at", -1))
    for s in sessions:
        s["_id"] = str(s["_id"])
        s["created_at"] = s["created_at"].isoformat()
    return jsonify({"sessions": sessions})


# Route to fetch message history for a given session
@ai_bp.route("/history/<session_id>", methods=["GET"])
def get_chat_history(session_id):
    messages = list(messages_collection.find({"session_id": session_id}).sort("timestamp", 1))
    for m in messages:
        m["_id"] = str(m["_id"])
        m["timestamp"] = m["timestamp"].isoformat()
    return jsonify({"messages": messages})


# Route to rename a session title
@ai_bp.route("/session/<session_id>/rename", methods=["PATCH"])
def rename_session(session_id):
    try:
        data = request.get_json()
        new_title = data.get("title", "").strip()
        if not new_title:
            return jsonify({"error": "Title is required"}), 400

        result = sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": {"title": new_title}}
        )
        if result.modified_count == 1:
            return jsonify({"message": "Session title updated."})
        else:
            return jsonify({"message": "No changes made."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# Route to generate financial summary cards

@ai_bp.route('/data_agent/cards', methods=['POST'])
def data_agent_cards_route():
    data = request.json
    prompt = "Generate financial summary cards"
    user_id = data["user_id"]
    agent = DataPresentationAgent()
    result = agent.run(prompt, user_id)
    return jsonify({ "cards": result.get("cards", []) })





@ai_bp.route('/data_agent/timeline', methods=['POST'])
def data_agent_timeline_route():
    data = request.json
    user_id = data["user_id"]
    from src.utils.data_agent_tools import get_timeline_data
    timeline = get_timeline_data(user_id)
    return jsonify({ "timeline": timeline })

@ai_bp.route('/data_agent/insight', methods=['POST'])
def insight_from_click():
    data = request.json
    user_id = data["user_id"]
    interaction = data["interaction"]
    agent = DataPresentationAgent()
    result = agent.generate_insight_from_click(user_id, interaction)
    return jsonify(result)

@ai_bp.route('/data_agent/simulate', methods=['POST'])
def simulate_user_goal():
    try:
        from src.agents.data_agent import DataAgent
        data = request.get_json()
        user_id = session.get("mobile_number", "anonymous")
        goal_type = data.get("goal_type", "")
        params = data.get("params", {})
        agent = DataAgent()
        result = agent.simulate_goal_pathway(user_id, goal_type, params)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({ "error": str(e) }), 500
