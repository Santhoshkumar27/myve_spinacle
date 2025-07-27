# src/services/session_store.py

# In-memory session store
session_store = {}

def create_session(session_id):
    session_store[session_id] = {
        "authenticated": False,
        "tools": [],
        "last_intent": None,
        "last_query": None
    }

def get_session(session_id):
    return session_store.get(session_id)

def set_authenticated(session_id, tools=None):
    if session_id in session_store:
        session_store[session_id]["authenticated"] = True
        if tools:
            session_store[session_id]["tools"] = tools

def is_authenticated(session_id):
    return session_store.get(session_id, {}).get("authenticated", False)

def get_tools(session_id):
    return session_store.get(session_id, {}).get("tools", [])

def set_last_intent(session_id, intent):
    if session_id in session_store:
        session_store[session_id]["last_intent"] = intent

def get_last_intent(session_id):
    return session_store.get(session_id, {}).get("last_intent")

def set_last_query(session_id, query):
    if session_id in session_store:
        session_store[session_id]["last_query"] = query

def get_last_query(session_id):
    return session_store.get(session_id, {}).get("last_query")


# MongoDB-backed session context storage
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["myve_db"]

def store_session_context(session_id, query, intent):
    db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"last_query": query, "last_intent": intent}},
        upsert=True
    )