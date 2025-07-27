"""
ResponseAgent

Role:
--------
The ResponseAgent serves as the intelligent orchestrator between all agents. It decides which agent to call, routes user queries to the appropriate logic, determines which datasets are required by each agent, and returns a natural, friendly answer.

Responsibilities:
------------------
- Detect user intent (assessment, plan, buy, explain).
- Determine required datasets for each intent.
- Route requests to the appropriate internal agent(s).
- Aggregate results and format into conversational, helpful messages.
- Maintain session memory and reuse past agent results if recent.
- Handle fallback if one agent fails or returns insufficient info.

Key Features:
--------------
- Role-based delegation: routes between PlanningAgent, BuyingAgent, AssessmentAgent.
- Selects data processors needed for each intent.
- Friendly natural language output based on structured agent data.
- Optionally augments with external agents (e.g. VisionAgent, BrowserTool).
- Smart formatting of cards, bullets, and tables in frontend.
- Logging and tracing for every agent decision step.

Tools/Libs Used:
----------------
- LangChain AgentExecutor: Enables complex tool-based routing and chaining of reasoning tasks (planned future enhancement).
- Pydantic schemas: Define strict input/output validation between agents, ensuring contract integrity.
- logging / loguru: Tracks internal agent calls and decisions for debugging and traceability.
- time-based caching (custom logic): Caches session results to reuse past insights and reduce redundant computation.
- transformers / peft (optional): For embedding-based or LLM-based intent detection.
- tiktoken or openai tokenizer: For token counting and prompt management.
- langchain.tools / langchain.agents: For future extensions to tool-based agent reasoning.
- cachetools or functools.lru_cache: For memory-efficient caching in long sessions.
"""



# Ensure this import is present at the top
from src.services.gemini_service import call_gemini
import logging
from typing import Dict, Any
from pydantic import BaseModel
from cachetools import TTLCache
from loguru import logger

# Ensure logger is available at the top for fallback error handling
logger_std = logging.getLogger(__name__)
# Optional imports
# from transformers import pipeline
# import tiktoken
# from langchain.agents import AgentExecutor
# from langchain.tools import Tool

class AgentResponse(BaseModel):
    response: str
    metadata: Dict[str, Any] = {}

# Example stubs for internal agents
from .buying_agent import BuyingAgent
from .planning_agent import PlanningAgent, PlanResponse
from .assessment_agent import AssessmentAgent
from .repaying_agent import RepayingAgent

class ResponseAgent:
    """
    The ResponseAgent orchestrates calls to internal agents based on user intent.
    It detects intent, selects the data processors needed for each intent, routes requests,
    and formats the responses.

    Stylistic guideline:
    - Keep responses short, crisp, and stat/data-oriented.
    - Conclude with a tone-appropriate encouragement — motivational, serious, or friendly based on user's intent or detected emotion.
    """
    def __init__(self):
        self.buying_agent = BuyingAgent()
        self.planning_agent = PlanningAgent()
        self.assess_agent = AssessmentAgent()
        self.repaying_agent = RepayingAgent()
        self.logger = logger.bind(agent="ResponseAgent")
        self.session_cache = TTLCache(maxsize=1000, ttl=3600)

    def get_cached_response(self, prompt: str, user_id: str) -> AgentResponse | None:
        session_key = f"{user_id}:{prompt.strip().lower()}"
        return self.session_cache.get(session_key)

    def cache_response(self, prompt: str, user_id: str, response: AgentResponse) -> None:
        session_key = f"{user_id}:{prompt.strip().lower()}"
        self.session_cache[session_key] = response

    def normalize_markdown(self, text: str) -> str:
        """
        Normalizes and formats markdown for sleek UI, including regional script filtering.
        """
        import re
        regional_pattern = r'[\u0900-\u097F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]'
        friendly_keywords = [
            "Namaste", "नमस्ते", "Shubh", "शुभ", "Congratulations", "बधाई", "Good luck", "शुभकामनाएं", "Welcome", "स्वागत"
        ]
        if re.search(regional_pattern, text):
            found_friendly = any(word in text for word in friendly_keywords)
            if not found_friendly:
                text = re.sub(regional_pattern, '', text)
        # Normalize and format for sleek UI
        text = re.sub(r'\n{2,}', '\n', text)
        text = re.sub(r"(?<!\n)[-•] ", r"\n• ", text)
        text = re.sub(r"(?<!\n)(\*\*[^*]+\*\*)", r"\n\n\1", text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def detect_emotion_tone(self, text: str) -> str:
        """
        Detects the emotional tone of the text using keyword analysis.
        """
        text_lower = text.lower()
        if any(kw in text_lower for kw in [
            "congratulations", "congrats", "badhai", "happy to share", "good news", "married", "baby", "promotion", "celebrate"
        ]):
            return "celebratory"
        elif any(kw in text_lower for kw in [
            "worried", "stressed", "urgent", "need help", "problem", "tension", "hospital", "medical", "lost job"
        ]):
            return "anxious"
        elif any(kw in text_lower for kw in [
            "goal", "plan", "future", "savings", "prepare", "dream", "study", "mba", "us", "canada", "growth", "improve"
        ]):
            return "motivational"
        elif any(kw in text_lower for kw in [
            "loan", "repay", "emi", "overdue", "debt"
        ]):
            return "serious"
        return "neutral"

    def append_closure(self, response: str, tone: str) -> str:
        """
        Appends a tone-based closure/ending to the response.
        """
        import re
        endings = {
            "celebratory": "\n\n🎉 Wishing you all the best!",
            "anxious": "\n\nLet's handle this one step at a time.",
            "motivational": "\n\n🚀 You’ve got this — time to take action!",
            "serious": "\n\nStay on track — every step counts.",
            "neutral": "\n\nLet me know if you'd like to explore more."
        }
        if tone in {"celebratory", "motivational"}:
            response += endings.get(tone, endings["neutral"])
        else:
            response += re.sub(r"^[^\w\s]*", "", endings.get(tone, endings["neutral"]))
        return response

    def format_natural_response(self, agent_output: AgentResponse) -> str:
        """
        Formats agent output for user. Adds section spacing, bullet normalization, and tone-specific closing.
        """
        response = agent_output.response or ""
        response = self.normalize_markdown(response)
        tone = self.detect_emotion_tone(response)
        response = self.append_closure(response, tone)
        return response.strip()

    def log_interaction(self, user_id: str, intent: str, success: bool) -> None:
        """Log basic interaction metadata."""
        self.logger.info(f"[User: {user_id}] Intent: {intent} | Success: {success}")

    def route(self, user_query: str, user_id: str) -> "AgentResponse":
        if user_query.startswith("[vision] "):
            skip_cache = True
            user_query = user_query[len("[vision] "):]
        else:
            skip_cache = False

        if not skip_cache:
            cached = self.get_cached_response(user_query, user_id)
            if cached:
                return cached

        schema = self.interpret_user_goal(user_query)

        # Override unsupported agents and keys with restricted list
        allowed_agents = {"buying_agent", "repaying_agent", "planning_agent", "assess_agent"}
        schema["agents"] = [a for a in schema.get("agents", []) if a in allowed_agents]

        allowed_data_keys = {"bank", "credit", "epf", "networth", "mf", "stock"}
        schema["data_keys"] = [k for k in schema.get("data_keys", []) if k in allowed_data_keys]
        intents = schema.get("intents", [])
        agents_to_run = schema["agents"]
        data_keys = schema["data_keys"] or ["bank", "credit", "networth", "epf", "mf", "stock"]

        self.logger.info(f"[ResponseAgent] Interpreted goal schema: {schema}")
        results = {}

        self.intent_map = {
            "buying": self.buying_agent,
            "repaying": self.repaying_agent,
            "planning": self.planning_agent,
            "assess": self.assess_agent
        }

        for agent_name in agents_to_run:
            agent_key = "assess" if agent_name == "assess_agent" else agent_name.replace("_agent", "")
            self.logger.debug(f"[ResponseAgent] intent_map keys: {list(self.intent_map.keys())}")
            agent = self.intent_map.get(agent_key)
            if not agent:
                self.logger.info(f"Skipped unsupported agent: {agent_name}")
                continue
            if hasattr(agent, "__call__"):
                self.logger.info(f"Calling agent {agent_key} with keys: {data_keys}")
                try:
                    results[agent_key] = agent(prompt=user_query, user_id=user_id, required_data_keys=data_keys)
                except Exception as e:
                    results[agent_key] = AgentResponse(response=f"{agent_key} failed: {e}", metadata={"agent": agent_key})

        # Chained Planning
        if "buying" in results and "planning" not in results:
            buying_meta = results["buying"].metadata or {}
            plan_data = buying_meta.get("plan")
            if plan_data:
                try:
                    self.logger.info("[ResponseAgent] Triggering planning_agent after buying_agent for multi-agent chaining.")
                    plan_prompt = f"Create a post-purchase financial plan for buying {buying_meta.get('item')} at ₹{buying_meta.get('price'):,}."
                    results["planning"] = self.planning_agent(prompt=plan_prompt, user_id=user_id, required_data_keys=data_keys)
                except Exception as e:
                    self.logger.warning(f"[ResponseAgent] Chained planning failed: {e}")
            if results.get("planning") and hasattr(results["planning"], "metadata"):
                plan_meta = results["planning"].metadata
                if isinstance(plan_meta, dict):
                    goals = plan_meta.get("goal", [])
                    for g in goals:
                        if isinstance(g, dict) and g.get("amount", 0) > 0 and g.get("timeline_months", 0) > 6:
                            try:
                                self.logger.info("[ResponseAgent] Triggering repaying_agent after planning_agent due to EMI implication.")
                                results["repaying"] = self.repaying_agent(prompt="Suggest repayment options for planned goal.", user_id=user_id, required_data_keys=data_keys)
                                break
                            except Exception as e:
                                self.logger.warning(f"[ResponseAgent] Chained repaying_agent failed: {e}")

        try:
            agent_outputs = []
            for k in schema.get("agents", []):
                agent_key = "assess" if k == "assess_agent" else k.replace("_agent", "")
                r = results.get(agent_key)
                if r and getattr(r, "response", None):
                    agent_outputs.append(r.response)

            if not agent_outputs:
                schema["agents"] = list(results.keys())
                return AgentResponse(
                    response="We couldn’t extract any financial advice based on the screen content. Try again with something more finance-related like expenses, purchases, offers, or savings.",
                    metadata=schema
                )

            item = schema.get("item", "your goal")
            category = schema.get("category", "")
            combined_prompt = (
                f"You are a smart financial assistant generating a complete, personalized summary for: {item} ({category}). "
                "Based on the insights from the following agents (buy, plan, repay, assess), produce a **structured, multi-section report**. "
                "Include:\n"
                "1. Financial Assessment\n"
                "2. Affordability Analysis\n"
                "3. Budget or Goal Planning\n"
                "4. Repayment Guidance (if applicable)\n"
                "5. Booking/Execution Tips\n"
                "6. Friendly Encouragement\n\n"
                "Structure each section with short paragraphs or bullet points, highlight key numbers in bold (₹, %, etc), "
                "and personalize the advice practically. Avoid vague encouragement. End with a motivational or friendly summary.\n\n"
                "=== Agent Insights ===\n"
            )
            combined_prompt += "\n\n".join([f"{i+1}. {resp}" for i, resp in enumerate(agent_outputs)])
            summary_text = call_gemini(prompt=combined_prompt, temperature=0.4)
            if summary_text:
                schema["agents"] = list(results.keys())
                return AgentResponse(response=summary_text.strip(), metadata=schema)
        except Exception as e:
            self.logger.warning(f"[ResponseAgent] Unified summarization failed: {e}")

        final_response = self.curate_response(results)
        schema["agents"] = list(results.keys())
        return AgentResponse(response=final_response, metadata=schema)
    def interpret_user_goal(self, prompt: str) -> Dict:
        import json
        import re
        import time

        def clean_json_block(text: str) -> str:
            """
            Extracts the first JSON block from a Gemini response even if narrative text precedes it.
            """
            json_match = re.search(r'\{.*?\}', text, re.DOTALL)
            if json_match:
                return json_match.group(0).strip()
            return "{}"

        retries = 4
        last_exc = None

        for attempt in range(retries):
            try:
                schema = call_gemini(
                    prompt=f"""Interpret this financial query and return JSON with:
                    - intents (list): buy, plan, assess, repay
                    - item (what is being bought or planned)
                    - category (bike, gold, education, surgery, etc.)
                    - urgency (low/medium/high)
                    - agents (e.g., buying_agent, planning_agent)
                    - data_keys (list of credit, bank, epf, mf, etc.)

                    Format response in English only with concise statistics. Use light regional complements (e.g., greeting or encouragement) if emotional tone is detected.

                    Respond in valid compact JSON.

                    User: {prompt}
                    """,
                    temperature=0.4
                )
                # Insert check for empty or invalid schema
                if not schema or not schema.strip():
                    self.logger.warning(f"[ResponseAgent] Gemini returned empty response for prompt: {prompt}")
                    raise ValueError("Empty or invalid Gemini response.")
                if schema.strip().startswith("<html"):
                    raise ValueError("Empty or invalid Gemini response.")
                schema = json.loads(clean_json_block(schema))
                # --- Normalize agents list to match intents ---
                intent_agent_map = {
                    "buy": "buying_agent",
                    "repay": "repaying_agent",
                    "plan": "planning_agent",
                    "assess": "assess_agent"
                }
                normalized_agents = [intent_agent_map[i] for i in schema.get("intents", []) if i in intent_agent_map]
                schema["agents"] = list(set(normalized_agents))
                # ------------------------------------------------
                return schema
            except Exception as e:
                last_exc = e
                self.logger.warning(f"[ResponseAgent] Gemini failed to parse schema on attempt {attempt+1}: {e}")
                self.logger.error(f"[ResponseAgent] Raw Gemini response: {schema if 'schema' in locals() else 'undefined'}")
                time.sleep(2 ** attempt)  # Exponential backoff

        # fallback logic
        fallback_intent = self.detect_intent(prompt)
        # Only allow supported agent types in fallback
        schema = {
            "intents": [fallback_intent],
            "agents": [f"{fallback_intent}_agent"] if fallback_intent in ["buy", "repay", "plan", "assess"] else [],
            "data_keys": ["credit", "bank"],
            "error": str(last_exc) if last_exc else "unknown"
        }
        # Additional fallback: pattern match for common keywords if schema is empty
        if not schema or not schema.get("intents") or not schema.get("agents"):
            for keyword in ["bike", "loan", "trip", "travel", "education", "surgery"]:
                if keyword in prompt.lower():
                    return {
                        "intents": ["plan"],
                        "item": keyword,
                        "category": keyword,
                        "urgency": "medium",
                        "agents": ["planning_agent"],
                        "data_keys": ["bank", "credit"]
                    }
        if not schema or not schema.get("intents") or not schema.get("agents"):
            # Defensive fallback
            return {
                "intents": ["plan"],
                "item": "",
                "category": "",
                "urgency": "medium",
                "agents": ["planning_agent"],
                "data_keys": ["bank", "credit"]
            }
        return schema

        self.intent_map = {
            "buying": self.buying_agent,
            "repaying": self.repaying_agent,
            "planning": self.planning_agent,
            "assess": self.assess_agent  # use 'assess' consistently
        }

        schema = interpret_user_goal(user_query)
        # Override unsupported agents and keys with restricted list
        allowed_agents = {"buying_agent", "repaying_agent", "planning_agent", "assess_agent"}
        schema["agents"] = [a for a in schema.get("agents", []) if a in allowed_agents]

        allowed_data_keys = {"bank", "credit", "epf", "networth", "mf", "stock"}
        schema["data_keys"] = [k for k in schema.get("data_keys", []) if k in allowed_data_keys]
        intents = schema.get("intents", [])
        agents_to_run = schema["agents"]
        data_keys = schema["data_keys"] or ["bank", "credit", "networth", "epf", "mf", "stock"]
        self.logger.info(f"[ResponseAgent] Interpreted goal schema: {schema}")
        results = {}
        for agent_name in agents_to_run:
            agent_key = "assess" if agent_name == "assess_agent" else agent_name.replace("_agent", "")
            self.logger.debug(f"[ResponseAgent] intent_map keys: {list(self.intent_map.keys())}")
            agent = self.intent_map.get(agent_key)
            if not agent:
                self.logger.info(f"Skipped unsupported agent: {agent_name}")
                continue
            if hasattr(agent, "__call__"):
                self.logger.info(f"Calling agent {agent_key} with keys: {data_keys}")
                try:
                    results[agent_key] = agent(prompt=user_query, user_id=user_id, required_data_keys=data_keys)
                except Exception as e:
                    results[agent_key] = AgentResponse(response=f"{agent_key} failed: {e}", metadata={"agent": agent_key})

        # Added logic to trigger planning_agent after buying_agent if conditions met
        if "buying" in results and "planning" not in results:
            buying_meta = results["buying"].metadata or {}
            plan_data = buying_meta.get("plan")
            if plan_data:
                try:
                    self.logger.info("[ResponseAgent] Triggering planning_agent after buying_agent for multi-agent chaining.")
                    plan_prompt = f"Create a post-purchase financial plan for buying {buying_meta.get('item')} at ₹{buying_meta.get('price'):,}."
                    results["planning"] = self.planning_agent(prompt=plan_prompt, user_id=user_id, required_data_keys=data_keys)
                except Exception as e:
                    self.logger.warning(f"[ResponseAgent] Chained planning failed: {e}")
            # Step 6: Trigger repaying_agent if EMI exists in planning result
            if results.get("planning") and hasattr(results["planning"], "metadata"):
                plan_meta = results["planning"].metadata
                if isinstance(plan_meta, dict):
                    goals = plan_meta.get("goal", [])
                    for g in goals:
                        if isinstance(g, dict) and g.get("amount", 0) > 0 and g.get("timeline_months", 0) > 6:
                            try:
                                self.logger.info("[ResponseAgent] Triggering repaying_agent after planning_agent due to EMI implication.")
                                results["repaying"] = self.repaying_agent(prompt="Suggest repayment options for planned goal.", user_id=user_id, required_data_keys=data_keys)
                                break
                            except Exception as e:
                                self.logger.warning(f"[ResponseAgent] Chained repaying_agent failed: {e}")

        # Summarize all agent responses using Gemini for a unified, crisp output
        try:
            # REPLACED agent_outputs listcomp with order-preserving logic
            agent_outputs = []
            for k in schema.get("agents", []):
                agent_key = "assess" if k == "assess_agent" else k.replace("_agent", "")
                r = results.get(agent_key)
                if r and getattr(r, "response", None):
                    agent_outputs.append(r.response)
            # Check for empty agent_outputs and return fallback message if so
            if not agent_outputs:
                schema["agents"] = list(results.keys())
                return AgentResponse(
                    response="We couldn’t extract any financial advice based on the screen content. Try again with something more finance-related like expenses, purchases, offers, or savings.",
                    metadata=schema
                )
            # Insert: fetch item/category for improved prompt context
            item = schema.get("item", "your goal")
            category = schema.get("category", "")
            combined_prompt = (
                f"You are a smart financial assistant generating a complete, personalized summary for: {item} ({category}). "
                "Based on the insights from the following agents (buy, plan, repay, assess), produce a **structured, multi-section report**. "
                "Include:\n"
                "1. Financial Assessment\n"
                "2. Affordability Analysis\n"
                "3. Budget or Goal Planning\n"
                "4. Repayment Guidance (if applicable)\n"
                "5. Booking/Execution Tips\n"
                "6. Friendly Encouragement\n\n"
                "Structure each section with short paragraphs or bullet points, highlight key numbers in bold (₹, %, etc), "
                "and personalize the advice practically. Avoid vague encouragement. End with a motivational or friendly summary.\n\n"
                "=== Agent Insights ===\n"
            )
            combined_prompt += "\n\n".join([f"{i+1}. {resp}" for i, resp in enumerate(agent_outputs)])
            summary_text = call_gemini(prompt=combined_prompt, temperature=0.4)
            if summary_text:
                schema["agents"] = list(results.keys())  # ensure agents = ['buying', 'planning', etc.]
                return AgentResponse(response=summary_text.strip(), metadata=schema)
        except Exception as e:
            self.logger.warning(f"[ResponseAgent] Unified summarization failed: {e}")

        final_response = self.curate_response(results)
        schema["agents"] = list(results.keys())  # ensure agents = ['buying', 'planning', etc.]
        return AgentResponse(response=final_response, metadata=schema)

    def curate_response(self, results: dict) -> str:
        """
        Curate multi-section response from agent results.
        Logs and skips empty or missing agent responses for transparency.
        """
        parts = []
        for key, val in results.items():
            if not val or not getattr(val, "response", None):
                self.logger.warning(f"[ResponseAgent] Skipping empty response from agent: {key}")
                fallback_message = {
                    "buy": "We couldn’t generate a purchase analysis right now. You may try again later or ask for help with your budget.",
                    "repay": "Repayment suggestions are currently unavailable. You can retry or consult financial support.",
                    "plan": "Planning advice could not be created at the moment. Please check your data or try rephrasing your goal.",
                    "assess": "Unable to analyze your financial health currently. You can retry or explore specific questions for better results."
                }.get(key, "No insight available.")
                parts.append(f"**{key.title()} Insight**\n{fallback_message}\n")
                continue
            agent_label = None
            # Try to get agent label from metadata
            if hasattr(val, "metadata") and isinstance(val.metadata, dict):
                agent_label = val.metadata.get("agent")
            # Normalize agent_label naming to be consistent
            if agent_label == "assessment":
                agent_label = "assess"
            # Map agent_label to emoji/section
            if agent_label == "buying" or key == "buy":
                section = "🛒 **Purchase Advice**"
            elif agent_label == "repaying" or key == "repay":
                section = "💳 **Debt Strategy**"
            elif agent_label == "planning" or key == "plan":
                section = "📈 **Future Plan Impact**"
            elif agent_label == "assess" or key == "assess":
                section = "📊 **Overall Financial Health**"
            else:
                section = f"**{key.title()}**"
            parts.append(f"{section}\n{val.response}\n")
        return "\n".join(parts)

    def detect_intent(self, prompt: str) -> str:
        """LLM-based multi-intent detection using Gemini with flexible combinations."""
        try:
            intent_prompt = (
                "You are a financial NLP model. Analyze the user's request and return one or more applicable intents.\n"
                "Available intents:\n"
                "- buy: for purchases (car, home, etc.)\n"
                "- plan: for financial planning or budgeting\n"
                "- assess: for analysis or summary of user's finances\n"
                "- repay: for repaying loans or bills\n\n"
                "Respond with a comma-separated list of intents (like 'assess,plan'), based on the user's message.\n"
                "If unsure, respond with 'unknown'.\n\n"
                f"User query: {prompt.strip()}\n"
                "Intents:"
            )
            intent_raw = call_gemini(intent_prompt, temperature=0.7).strip().lower()
            intents = [i.strip() for i in intent_raw.split(",") if i.strip() in {"buy", "plan", "assess", "repay"}]
            return ",".join(intents) if intents else "unknown"
        except Exception as e:
            self.logger.error(f"Intent detection failed: {e}")
            return "unknown"
    def route_with_schema(self, user_query: str, user_id: str, schema_override: Dict[str, Any]) -> AgentResponse:
        schema = schema_override

        allowed_agents = {"buying_agent", "repaying_agent", "planning_agent", "assess_agent"}
        schema["agents"] = [a for a in schema.get("agents", []) if a in allowed_agents]

        allowed_data_keys = {"bank", "credit", "epf", "networth", "mf", "stock"}
        schema["data_keys"] = [k for k in schema.get("data_keys", []) if k in allowed_data_keys]

        intents = schema.get("intents", [])
        agents_to_run = schema["agents"]
        data_keys = schema["data_keys"] or ["bank", "credit", "networth", "epf", "mf", "stock"]

        self.logger.info(f"[ResponseAgent] Running route_with_schema with: {schema}")
        results = {}

        self.intent_map = {
            "buying": self.buying_agent,
            "repaying": self.repaying_agent,
            "planning": self.planning_agent,
            "assess": self.assess_agent
        }

        for agent_name in agents_to_run:
            agent_key = "assess" if agent_name == "assess_agent" else agent_name.replace("_agent", "")
            self.logger.debug(f"[ResponseAgent] intent_map keys: {list(self.intent_map.keys())}")
            agent = self.intent_map.get(agent_key)
            if not agent:
                self.logger.info(f"Skipped unsupported agent: {agent_name}")
                continue
            if hasattr(agent, "__call__"):
                self.logger.info(f"Calling agent {agent_key} with keys: {data_keys}")
                try:
                    results[agent_key] = agent(prompt=user_query, user_id=user_id, required_data_keys=data_keys)
                except Exception as e:
                    results[agent_key] = AgentResponse(response=f"{agent_key} failed: {e}", metadata={"agent": agent_key})

        # Unified summary logic (copy from existing `route` logic)
        try:
            agent_outputs = []
            for k in schema.get("agents", []):
                agent_key = "assess" if k == "assess_agent" else k.replace("_agent", "")
                r = results.get(agent_key)
                if r and getattr(r, "response", None):
                    agent_outputs.append(r.response)

            if not agent_outputs:
                schema["agents"] = list(results.keys())
                return AgentResponse(
                    response="We couldn’t extract any financial advice based on the screen content. Try again with something more finance-related like expenses, purchases, offers, or savings.",
                    metadata=schema
                )

            item = schema.get("item", "your goal")
            category = schema.get("category", "")
            combined_prompt = (
                f"You are summarizing financial advice for: {item} ({category}). "
                "Based on the following agent insights, produce a clear, concise, practical answer without hallucinations. "
                "Keep it logical and user-friendly.\n\n"
            )
            combined_prompt += "\n\n".join([f"{i+1}. {resp}" for i, resp in enumerate(agent_outputs)])
            summary_text = call_gemini(prompt=combined_prompt, temperature=0.4)
            if summary_text:
                schema["agents"] = list(results.keys())
                return AgentResponse(response=summary_text.strip(), metadata=schema)
        except Exception as e:
            self.logger.warning(f"[ResponseAgent] Unified summarization failed in route_with_schema: {e}")

        final_response = self.curate_response(results)
        schema["agents"] = list(results.keys())
        return AgentResponse(response=final_response, metadata=schema)