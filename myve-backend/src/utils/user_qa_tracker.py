from pymongo import MongoClient
import datetime
import os

# MongoDB connection (adjust URI as needed)
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client["myve_ai"]
qa_collection = db["qa_logs"]

def track_user_qa(session_id, user_query, ai_response, intent=None, probes=None, final_decision_summary=None, goal_metadata=None):
    """
    Logs a Q&A entry with optional intent, follow-up probes, decision summary, and goal metadata into MongoDB.
    """
    entry = {
        "session_id": session_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "user_query": user_query,
        "ai_response": ai_response,
        "intent": intent,
        "probes": probes or [],
        "final_decision_summary": final_decision_summary,
        "goal_metadata": goal_metadata
    }

    qa_collection.insert_one(entry)
    print(f"[QA TRACKER] Logged to DB: {entry['timestamp']} - {user_query[:50]}...")

def get_session_qa(session_id):
    """
    Returns all tracked Q&A for a given session from MongoDB.
    """
    return list(qa_collection.find({"session_id": session_id}))