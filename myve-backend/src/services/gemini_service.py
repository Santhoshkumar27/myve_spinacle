



import os
import json
import asyncio
import logging
import re

import google.generativeai as genai
from dotenv import load_dotenv
from flask import session as flask_session

from src.models.sessions import sessions_collection
from src.models.messages import messages_collection
from src.utils import plan_builder, response_builder
from src.services import mcp_client
from src.database import json_mongo
from src.agent_orchestrator import AgentDataOrchestrator

# Add required imports for plan_builder and response_builder
from src.utils import plan_builder, response_builder

from src.database import json_mongo

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Define model with no baked-in system instruction
model = genai.GenerativeModel(model_name="gemini-2.5-flash")


async def fetch_mcp_context(mobile_number):
    context_parts = []
    context_parts.append("## User Financial Overview")
    # --- Robust fetches with try/except per client call ---
    try:
        try:
            net = await json_mongo.fetch_networth(mobile_number)
        except Exception as e:
            net = {}
            logging.warning(f"[WARN] Could not fetch networth for {mobile_number}: {e}")

        try:
            credit = await json_mongo.fetch_credit(mobile_number)
        except Exception as e:
            credit = []
            logging.warning(f"[WARN] Could not fetch credit data for {mobile_number}: {e}")

        try:
            assets = await json_mongo.fetch_assets(mobile_number)
        except Exception as e:
            assets = []
            logging.warning(f"[WARN] Could not fetch assets for {mobile_number}: {e}")

        try:
            mf_txns = await json_mongo.fetch_mf_transactions(mobile_number)
        except Exception as e:
            mf_txns = []
            logging.warning(f"[WARN] Could not fetch mutual fund transactions: {e}")

        try:
            bank_txns = await json_mongo.fetch_bank_transactions(mobile_number)
        except Exception as e:
            bank_txns = []
            logging.warning(f"[WARN] Could not fetch bank transactions: {e}")

        try:
            stock_txns = await json_mongo.fetch_stock_transactions(mobile_number)
        except Exception as e:
            stock_txns = []
            logging.warning(f"[WARN] Could not fetch stock transactions: {e}")

        # Add markdown-style header at the top (already done above)

        # Net Worth
        print("[DEBUG] Networth raw:", net)
        if net and "netWorth" in net:
            net_summary = net["netWorth"]
            currency = net_summary.get("currencyCode", "INR")
            value = net_summary.get("units", "unknown")
            context_parts.append(f"**Net worth:** ₹{value} ({currency})")

            nw_response = net.get("netWorthResponse", {})
            if "assetValues" in nw_response:
                context_parts.append("### Assets Breakdown:")
                for asset in nw_response["assetValues"]:
                    label = asset.get("netWorthAttribute", "Unknown")
                    val = asset.get("value", {}).get("units", "0")
                    context_parts.append(f"- {label.replace('_', ' ').title()}: ₹{val}")
            if "liabilityValues" in nw_response:
                context_parts.append("### Liabilities Breakdown:")
                for liab in nw_response["liabilityValues"]:
                    label = liab.get("netWorthAttribute", "Unknown")
                    val = liab.get("value", {}).get("units", "0")
                    context_parts.append(f"- {label.replace('_', ' ').title()}: ₹{val}")
        else:
            context_parts.append("**Net worth:** (data not available)")

        # Credit Score and Report Summary (from networth)
        credit_score = net.get("creditScore", {}).get("summary", {}).get("score", "N/A") if net else "N/A"
        context_parts.append(f"**Credit Score:** {credit_score}")

        # Credit Report Summary
        if credit and isinstance(credit, list) and len(credit) > 0:
            report = credit[0].get("creditReportData", {})
            summary = report.get("creditAccount", {}).get("creditAccountSummary", {})
            account_summary = summary.get("account", {})
            outstanding = summary.get("totalOutstandingBalance", {}).get("outstandingBalanceAll", "N/A")
            context_parts.append("### Credit Report Summary:")
            context_parts.append(f"- Total Accounts: {account_summary.get('creditAccountTotal', '?')}")
            context_parts.append(f"- Active Accounts: {account_summary.get('creditAccountActive', '?')}")
            context_parts.append(f"- Defaults: {account_summary.get('creditAccountDefault', '?')}")
            context_parts.append(f"- Total Outstanding: ₹{outstanding}")

            # Credit Account-wise Details (Deeper reasoning)
            credit_accounts = report.get("creditAccount", {}).get("creditAccountDetails", [])
            if credit_accounts:
                context_parts.append("### Credit Account Insights:")
                for acct in credit_accounts:
                    institute = acct.get("subscriberName", "N/A")
                    acct_type = acct.get("accountType", "Unknown")
                    status = acct.get("accountStatus", "N/A")
                    opened = acct.get("openDate", "N/A")
                    balance = acct.get("currentBalance", "0")
                    overdue = acct.get("amountPastDue", "0")
                    rating = acct.get("paymentRating", "N/A")
                    roi = acct.get("rateOfInterest", "N/A")
                    tenure = acct.get("repaymentTenure", "N/A")
                    last_reported = acct.get("dateReported", "N/A")
                    profile = acct.get("paymentHistoryProfile", "N/A")

                    context_parts.append(
                        f"- **{acct_type}** from *{institute}*: Status {status}, Opened {opened}, "
                        f"Balance ₹{balance}, Overdue ₹{overdue}, ROI {roi}%, Payment Rating {rating}, "
                        f"Tenure {tenure}, Last Reported {last_reported}, History {profile}"
                    )

            # CAPS Summary and Applications
            caps_summary = report.get("caps", {}).get("capsSummary", {})
            if caps_summary:
                context_parts.append("### CAPS Inquiry Summary:")
                context_parts.append(f"- CAPS Last 180 Days: {caps_summary.get('capsLast180Days', 'N/A')}")
                context_parts.append(f"- CAPS Last 30 Days: {caps_summary.get('capsLast30Days', 'N/A')}")
                context_parts.append(f"- Total CAPS Inquiries: {caps_summary.get('totalCapsEnquiries', 'N/A')}")

            caps_apps = report.get("caps", {}).get("capsApplicationDetailsArray", [])
            if caps_apps:
                context_parts.append("### CAPS Application Records:")
                for app in caps_apps[:3]:  # Limit to 3 most recent
                    date = app.get("applicationDate", "N/A")
                    type_ = app.get("enquiryPurpose", "N/A")
                    amt = app.get("applicationAmount", "N/A")
                    lender = app.get("subscriberName", "N/A")
                    context_parts.append(f"- {type_} for ₹{amt} at {lender} on {date}")

            # Credit Profile Header & Match Result
            header = report.get("creditProfileHeader", {})
            match = report.get("matchResult", {})
            message = report.get("userMessage", {})

            if header:
                context_parts.append("### Credit Report Metadata:")
                context_parts.append(f"- Report Date: {header.get('reportDate', 'N/A')} at {header.get('reportTime', 'N/A')}")

            if match:
                context_parts.append(f"- Match Type: {match.get('matchType', 'N/A')}")

            if message:
                context_parts.append(f"- User Message: {message.get('userMessageText', 'N/A')}")

        # EPF
        epf_data = net.get("epf", {}) if net else {}
        if epf_data:
            context_parts.append(f"**EPF accounts:** {len(epf_data)} connected.")

        # Assets
        if assets:
            context_parts.append(f"**Asset categories detected:** {len(assets)}")

        # Mutual Fund Transactions
        context_parts.append("### Recent Mutual Fund Transactions:")
        txn_count = 0
        for scheme in mf_txns:
            scheme_name = scheme.get("schemeName", "Unknown Scheme")
            txns = scheme.get("txns", [])
            for txn in txns:
                if txn_count >= 5:
                    break
                txn_type = "BUY" if txn[0] == 1 else "SELL"
                date = txn[1] if len(txn) > 1 else "Unknown date"
                amount = txn[4] if len(txn) > 4 else "0"
                context_parts.append(f"- **₹{amount}** on *{date}* ({txn_type}, {scheme_name})")
                txn_count += 1
            if txn_count >= 5:
                break

        # Bank Transactions
        context_parts.append("### Recent Bank Transactions:")
        txn_count = 0
        for bank in bank_txns:
            bank_name = bank.get("bank", "Unknown Bank")
            txns = bank.get("txns", [])
            for txn in txns:
                if txn_count >= 5:
                    break
                amount = txn[0] if len(txn) > 0 else "0"
                narration = txn[1] if len(txn) > 1 else "No description"
                date = txn[2] if len(txn) > 2 else "Unknown date"
                context_parts.append(f"- **₹{amount}** on *{date}* ({bank_name}): {narration}")
                txn_count += 1
            if txn_count >= 5:
                break

        # Stock Transactions
        context_parts.append("### Recent Stock Transactions:")
        txn_count = 0
        for stock in stock_txns:
            isin = stock.get("isin", "Unknown ISIN")
            txns = stock.get("txns", [])
            for txn in txns:
                if txn_count >= 5:
                    break
                txn_type_code = txn[0] if len(txn) > 0 else 0
                txn_type = {1: "BUY", 2: "SELL", 3: "BONUS", 4: "SPLIT"}.get(txn_type_code, "UNKNOWN")
                date = txn[1] if len(txn) > 1 else "Unknown date"
                quantity = txn[2] if len(txn) > 2 else "?"
                nav = txn[3] if len(txn) > 3 else "?"
                context_parts.append(f"- *{txn_type}* {quantity} units on **{date}** at NAV ₹{nav} (ISIN: {isin})")
                txn_count += 1
            if txn_count >= 5:
                break

        # ---- Begin: Financial Insights/Reasoning Section ----
        insights = []
        # 1. Compute Total EMIs, Debt-to-income %, Surplus income after EMIs/SIPs, Overdue/defaults, Asset buffer
        try:
            # Try to extract monthly income (from networth if possible)
            monthly_income = None
            if net and "netWorthResponse" in net:
                income_vals = net["netWorthResponse"].get("assetValues", [])
                for asset in income_vals:
                    if asset.get("netWorthAttribute", "").lower() in ["annual_income", "monthly_income"]:
                        # If annual, divide by 12
                        val = asset.get("value", {}).get("units", None)
                        if val is not None:
                            if asset.get("netWorthAttribute", "").lower() == "annual_income":
                                monthly_income = float(val) / 12.0
                            else:
                                monthly_income = float(val)
            # Fallback: try to estimate from bank txns (very rough)
            if monthly_income is None and bank_txns:
                # Take average of all positive transactions in last 5 bank txns
                incomes = []
                for bank in bank_txns:
                    txns = bank.get("txns", [])
                    for txn in txns[:5]:
                        amount = float(txn[0]) if len(txn) > 0 else 0
                        if amount > 0:
                            incomes.append(amount)
                if incomes:
                    monthly_income = sum(incomes) / len(incomes)

            # 2. Total EMIs (from credit accounts)
            total_emi = 0.0
            total_outstanding = 0.0
            total_overdue = 0.0
            num_overdue_accounts = 0
            total_defaults = 0
            if credit and isinstance(credit, list) and len(credit) > 0:
                report = credit[0].get("creditReportData", {})
                credit_accounts = report.get("creditAccount", {}).get("creditAccountDetails", [])
                for acct in credit_accounts:
                    emi = acct.get("emiAmount")
                    if emi is not None:
                        try:
                            total_emi += float(emi)
                        except Exception:
                            pass
                    # Outstanding
                    balance = acct.get("currentBalance", None)
                    if balance is not None:
                        try:
                            total_outstanding += float(balance)
                        except Exception:
                            pass
                    # Overdue
                    overdue = acct.get("amountPastDue", None)
                    if overdue is not None:
                        try:
                            overdue_val = float(overdue)
                            total_overdue += overdue_val
                            if overdue_val > 0:
                                num_overdue_accounts += 1
                        except Exception:
                            pass
                    # Defaults (from paymentRating)
                    rating = acct.get("paymentRating", "")
                    if "DEFAULT" in str(rating).upper():
                        total_defaults += 1
            # 3. SIPs (from mutual fund txns)
            total_sip = 0.0
            if mf_txns:
                for scheme in mf_txns:
                    txns = scheme.get("txns", [])
                    for txn in txns:
                        if len(txn) > 0 and txn[0] == 1:  # BUY
                            amount = float(txn[4]) if len(txn) > 4 else 0
                            total_sip += amount
            # 4. Asset buffer (EPF/MF/stocks)
            asset_buffer = 0.0
            # Add up values from networth: assetValues for EPF, MF, stocks
            if net and "netWorthResponse" in net:
                asset_vals = net["netWorthResponse"].get("assetValues", [])
                for asset in asset_vals:
                    label = asset.get("netWorthAttribute", "").lower()
                    val = asset.get("value", {}).get("units", None)
                    if val is not None:
                        if any(x in label for x in ["epf", "mutual", "stock", "equity"]):
                            try:
                                asset_buffer += float(val)
                            except Exception:
                                pass
            # 5. Debt-to-income ratio
            dti = None
            if monthly_income and total_emi > 0:
                dti = (total_emi / monthly_income) * 100.0
            # 6. Surplus after EMIs and SIPs
            surplus_income = None
            if monthly_income is not None:
                surplus_income = monthly_income - total_emi - total_sip
            # Compose insights
            insights.append("### Financial Health Insights:")
            if total_emi > 0:
                insights.append(f"- **Total monthly EMIs:** ₹{round(total_emi)}")
            if dti is not None:
                insights.append(f"- **Debt-to-Income Ratio:** {dti:.1f}%")
            if surplus_income is not None:
                insights.append(f"- **Estimated Surplus Income after EMIs and SIPs:** ₹{round(surplus_income)}")
            if num_overdue_accounts > 0 or total_overdue > 0:
                insights.append(f"- **Overdue credit accounts:** {num_overdue_accounts}, **Total overdue amount:** ₹{round(total_overdue)}")
            if total_defaults > 0:
                insights.append(f"- **Defaults detected:** {total_defaults} account(s)")
            if asset_buffer > 0:
                insights.append(f"- **Asset fallback buffer (EPF/MF/stocks):** ₹{round(asset_buffer)}")
        except Exception as insight_ex:
            insights.append(f"- [Insight error: {insight_ex}]")
        # Inject insights near the end of the context block, before logging/return
        context_parts.extend(insights)
        # ---- End: Financial Insights/Reasoning Section ----
        logging.info(f"[CONTEXT] Final assembled user context for {mobile_number}:\n" + "\n".join(context_parts))
        return "\n".join(context_parts)
    except Exception as e:
        logging.exception(f"[ERROR] Unexpected error in fetch_mcp_context for {mobile_number}: {e}")
        raise


async def ask_gemini(prompt, mobile_number=None, probing_answers=None, intent=None, prompt_type=None):
    try:
        context = ""
        if mobile_number:
            context = await fetch_mcp_context(mobile_number)
            if probing_answers:
                if isinstance(probing_answers, dict):
                    probing_summary = "\n".join([f"- {key}: {val}" for key, val in probing_answers.items()])
                elif isinstance(probing_answers, list):
                    probing_summary = "\n".join([f"- {ans}" for ans in probing_answers])
                else:
                    probing_summary = str(probing_answers)
                context += f"\n\n### Additional Info from User:\n{probing_summary}"
            if intent:
                context += f"\n\nIntent: {intent}"
            if prompt_type:
                context += f"\nPrompt Type: {prompt_type}"
            print("[DEBUG] Context for Gemini:\n", context)

            # --- BEGIN: INTENT DETECTION AND ORCHESTRATOR WIRING ---
            import json
            # Refactored to use AgentDataOrchestrator class
            from src.agent_orchestrator import AgentDataOrchestrator
            orchestrator = AgentDataOrchestrator()
            if not intent:
                intent = await orchestrator.detect_intent(prompt)
            print(f"[DEBUG] Detected intent: {intent}")
            data_response = await orchestrator.fetch_data_for_intent(intent, mobile_number)
            context += f"\n\n---\nIntent-Matched Data:\n{json.dumps(data_response, indent=2)}"
            # --- END: INTENT DETECTION AND ORCHESTRATOR WIRING ---

            from flask import session as flask_session

            session_id = flask_session.get("active_session")
            history_snippets = []
            if session_id:
                past_msgs = list(messages_collection.find(
                    {"session_id": session_id},
                    {"role": 1, "message": 1}
                ).sort("timestamp", 1))  # ascending to maintain chronological order

                for msg in past_msgs[-8:]:  # take last 8 messages
                    role = msg.get("role", "user")
                    content = msg.get("message", "")
                    label = "User" if role == "user" else "Assistant"
                    history_snippets.append(f"{label}: {content}")

            chat_history_block = "Chat History:\n" + "\n".join(history_snippets)

            prompt = (
                "You are a highly knowledgeable and memory-aware personal financial adviser named Myve AI. "
                "Use the user's financial history and context provided below to give relevant, precise, and personalized advice. "
                "Keep the tone helpful, polite, and practical.\n\n"
                f"{chat_history_block}\n\n"
                f"---\nUser Financial Context:\n{context}\n---\n\n"
                f"User's Question:\n{prompt}"
            )
            if probing_answers:
                if isinstance(probing_answers, dict):
                    formatted_clarifications = "\n- " + "\n- ".join([f"{k}: {v}" for k, v in probing_answers.items()])
                elif isinstance(probing_answers, list):
                    formatted_clarifications = "\n- " + "\n- ".join(probing_answers)
                else:
                    formatted_clarifications = f"\n- {str(probing_answers)}"
                prompt += f"\n\nUser clarified:{formatted_clarifications}"

            # Store latest context in session document
            from flask import session as flask_session
            session_id = flask_session.get("active_session")
            if session_id:
                sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"latest_context": context}}
                )

        response = model.generate_content(prompt)
        if not hasattr(response, 'text') or not response.text:
            raise ValueError("Gemini returned no text response.")
        try:
            result_json = json.loads(response.text)
            return result_json, context
        except json.JSONDecodeError:
            print("[WARN] Gemini response not JSON — fallback to raw text")
            import re
            parsed_surplus = 0
            parsed_expenses = 0
            parsed_sip = 0
            parsed_outstanding = 0
            parsed_asset_buffer = 0
            parsed_overdue = 0
            try:
                surplus_match = re.search(r"Estimated Surplus Income.*?: ₹([\d,]+)", context)
                if surplus_match:
                    parsed_surplus = int(surplus_match.group(1).replace(",", ""))
                debt_match = re.search(r"Total Outstanding.*?: ₹([\d,]+)", context)
                if debt_match:
                    parsed_outstanding = int(debt_match.group(1).replace(",", ""))
                buffer_match = re.search(r"Asset fallback buffer.*?: ₹([\d,]+)", context)
                if buffer_match:
                    parsed_asset_buffer = int(buffer_match.group(1).replace(",", ""))
                # Insert overdue parsing after buffer_match
                overdue_match = re.search(r"Total overdue amount.*?: ₹([\d,]+)", context)
                if overdue_match:
                    parsed_overdue = int(overdue_match.group(1).replace(",", ""))
                else:
                    parsed_overdue = 0
            except Exception:
                pass
            user_context_dict = {
                "income": parsed_surplus + parsed_expenses + parsed_sip,
                "expenses": parsed_expenses,
                "total_debt": parsed_outstanding,
                "total_savings": parsed_asset_buffer,
                "surplus": parsed_surplus,
                "overdue_amount": parsed_overdue
            }
            plan = plan_builder.build_action_plan(intent or "unknown", probing_answers or {}, user_context_dict)
            formatted = ""
            try:
                formatted = response_builder.build_financial_advice_response(prompt, plan)
            except Exception as format_error:
                print("[ERROR] Failed to format response using response_builder:", format_error)
                # Build a manual fallback using plan details
                steps = plan.get("steps", [])
                if steps:
                    step_lines = "\n".join([f"- {step.get('task')}: {step.get('details')}" for step in steps])
                    formatted = f"Here's a step-by-step plan:\n{step_lines}"
                else:
                    formatted = "I couldn't format a complete response, but here's the basic plan:\n" + str(plan)
            return {"text": formatted, "plan": plan}, context
    except Exception as e:
        raise


# New assessment agent function
def askassess(prompt: str, financial_data: dict) -> str:
    try:
        context = "You are an Assessment Agent — a personalized financial assistant for evaluating user financial health based on available data. Your job is to:\n"
        context += json.dumps(financial_data, indent=2)

        prompt_text = (
            f"{context}\n\n"
            f"The user has asked:\n\"{prompt}\"\n\n"
            f"Based on the above data, answer this specific question. "
            f"Be clear, honest, and friendly. Use simple, informal Indian English like a money coach. "
            f"Don't just summarize stats — reason from them. End with answering the user question."
        )
        prompt_text += (
            "\n\n---\n"
            "Provide a financial health check:\n"
            "1. Strengths (e.g., surplus, savings)\n"
            "2. Weaknesses (e.g., debt, overdue)\n"
            "3. Score: Good / Moderate / Poor\n"
            "5. 1 long-term goal\n\n"
            "Be crisp, use bullets, bold numbers, and end on an encouraging note."
        )

        response = model.generate_content(prompt_text)
        if not hasattr(response, 'text') or not response.text:
            raise ValueError("Gemini returned no text response.")
        return {"text": response.text.strip(), "raw_prompt": prompt_text}
    except Exception as e:
        logging.exception("[askassess] Error generating assessment:")
        return {"text": f"Error generating assessment: {str(e)}"}

async def suggest_next_queries(prompt, response_text):
    try:
        suggestion_prompt = f"""
You are a financial assistant. Based on the following conversation, suggest exactly 3 follow-up financial questions the user might ask next.

User asked: {prompt}
You replied: {response_text}

Respond only with a raw JSON list of strings, like this:

[
  "What is my monthly savings rate?",
  "Compare my asset growth this year",
  "Am I overspending on any category?"
]
"""
        result = model.generate_content(suggestion_prompt)
        print("[DEBUG] Suggestion raw response:", result.text)
        return json.loads(result.text.strip().strip("```json").strip("```"))[:3]
    except json.JSONDecodeError:
        print("[ERROR] Gemini did not return valid JSON:", result.text)
        return [
            "What else should I know about my finances?",
            "Show me my credit trends",
            "Any unusual activity in my accounts?"
        ]
    except Exception as e:
        print("Suggestion error:", e)
        return [
            "What else should I know about my finances?",
            "Show me my credit trends",
            "Any unusual activity in my accounts?"
        ]


async def detect_intent_from_query(query: str) -> str:
    try:
        intent_prompt = f"""
You are a financial NLP model. Given the user's query below, return the best-matching financial intent.

Query: {query}

Respond with only one of the following:
- bank_transactions
- credit_summary
- investment_portfolio
- net_worth
- loan_status
- general_summary
- unknown

Only return the intent label, nothing else.
"""
        result = model.generate_content(intent_prompt)
        intent = result.text.strip().lower()
        allowed_intents = [
            "bank_transactions",
            "credit_summary",
            "investment_portfolio",
            "net_worth",
            "loan_status",
            "general_summary",
            "unknown"
        ]
        if intent not in allowed_intents:
            return "unknown"
        return intent
    except Exception as e:
        print("[ERROR] Intent detection failed:", e)
        return "unknown"


def call_gemini(prompt: str, temperature: float = 0.7) -> str:
    """
    Central Gemini access function for all agents.
    Accepts prompt and returns Gemini's best guess response.
    """
    assert isinstance(temperature, float), f"Temperature must be float, got {type(temperature)}: {temperature}"
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": float(temperature),
                "top_p": 1,
                "top_k": 32,
                "max_output_tokens": 2048
            }
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini ERROR]: {str(e)}")
        return "I couldn’t process that right now. Please try again."

# Financial intent detection (simple classifier for banking/finance domains)
def detect_financial_intent(query):
    prompt = f"Classify this query into one of: bank_transactions, mutual_funds, credit_summary, stock_holdings, networth, loans, general_summary.\nQuery: {query}\nIntent:"
    response = model.generate_content(prompt)
    return response.text.strip().lower()


# Gemini-powered intent classification method (async)
async def detect_intent_gemini(query: str) -> str:
    """
    Detects user intent using Gemini based on the financial query.
    Returns one of the allowed intent labels.
    """
    try:
        intent_prompt = f"""
You are a financial NLP model. Given the user's query below, return the best-matching financial intent.

Query: {query}

Respond with only one of the following:
- bank_transactions
- credit_summary
- investment_portfolio
- net_worth
- loan_status
- general_summary
- buying_intent
- planning_intent
- repayment_intent
- unknown

Only return the intent label, nothing else.
"""
        result = call_gemini(intent_prompt)
        intent = result.strip().lower()
        allowed_intents = [
            "bank_transactions",
            "credit_summary",
            "investment_portfolio",
            "net_worth",
            "loan_status",
            "general_summary",
            "buying_intent",
            "planning_intent",
            "repayment_intent",
            "unknown"
        ]
        return intent if intent in allowed_intents else "unknown"
    except Exception as e:
        print(f"[Gemini Intent ERROR]: {e}")
        return "unknown"
    
async def ask_gemini_from_vision(context_text, query, force_strict_mode=False):
    try:
        vision_prompt = (
            "You are Myve Vision, a personal financial assistant that analyzes screenshots for visual financial context. "
            "Given the extracted screen image text and user question, your job is to:\n"
            "- Identify if there is any meaningful product, item, or financial element in the image.\n"
            "- If the image is empty or has no product context, say: 'I couldn't identify any financial item in this screenshot. Please provide more details or try another view.'\n"
            "- If a product (like a bike, car, laptop, or service) is visible, describe it briefly.\n"
            "- Use the user's financial net worth and credit report (assumed to be known) to advise if this item can be purchased.\n"
            "- If it's a big-ticket item (like car or house), and finances don’t look healthy, give friendly suggestions like: 'This might be a stretch now, but let's work toward it together. Here's how…'\n"
            "- If it's affordable, say: 'Yes, this seems manageable for you. You can go ahead, but also keep track of monthly costs.'\n"
            "- Be friendly, practical, and helpful. Don’t repeat user queries. Speak like a supportive companion.\n\n"
            f"Context:\n{context_text}\n\n"
            f"User's Question:\n{query}"
        )
        if force_strict_mode:
            vision_prompt += (
                "\n- IMPORTANT: Do not sugarcoat. Be direct, but friendly. Flag risks. Prioritize user’s long-term financial health."
            )
            vision_prompt += (
                "\n- You must guide the user to take control of their finances, even if it's not easy to hear. "
                "Suggest improvements, restructure plans, and if needed, give a time-based goal for when a purchase might be feasible."
            )
        response = model.generate_content(vision_prompt)
        if not hasattr(response, 'text') or not response.text:
            raise ValueError("Gemini response is empty or malformed.")
        return response.text.strip()
    except Exception as e:
        return f"Error in Gemini Vision Advisory: {e}"
# New planning agent function
def askplan(prompt: str, planning_data: dict) -> str:
    try:
        # Shortened context (avoid full nested dump)
        summary_context = "You are a Planning Agent who helps users plan investments or savings.\n"
        summary_context += "Use this user snapshot:\n"
        summary_context += f"- Net Worth: ₹{planning_data.get('net_worth', 'N/A')}\n"
        summary_context += f"- Monthly Income: ₹{planning_data.get('income', 'N/A')}\n"
        summary_context += f"- Expenses: ₹{planning_data.get('expenses', 'N/A')}\n"
        summary_context += f"- Surplus: ₹{planning_data.get('surplus', 'N/A')}\n"
        summary_context += f"- SIPs: ₹{planning_data.get('sip', 'N/A')}\n"
        summary_context += f"- Debt: ₹{planning_data.get('debt', 'N/A')}\n"

        prompt_text = (
            f"{summary_context}\n\n"
            f"The user has asked:\n\"{prompt}\"\n\n"
            f"Provide a realistic step-by-step savings or investment roadmap. Include:\n"
            "1. Goal Summary (amount + timeline)\n"
            "2. Monthly saving/investment target\n"
            "3. Instruments to use (MF, SIP, FD, etc)\n"
            "4. Risk or priority tips\n"
            "5. Motivational encouragement\n\n"
            "Respond in structured format with bullets. Bold key ₹ numbers. Avoid generic fluff."
        )

        response = model.generate_content(prompt_text)
        return {"text": response.text.strip(), "raw_prompt": prompt_text}
    except Exception as e:
        logging.exception("[askplan] Error generating planning guidance:")
        return {"text": f"Planning failed. Please try again later.\nReason: {str(e)}"}

# Repayment agent function
def askrepay(prompt: str, repayment_data: dict) -> str:
    try:
        context = (
            "You are a Repayment Agent — a personalized debt advisor who helps users reduce financial stress by paying down credit card dues, loans, or EMIs. "
            "Use the structured financial data below to evaluate both Snowball and Avalanche strategies, estimate payoff timelines, and guide the user with clear, practical advice. "
            "Speak in friendly, simple Indian English like a financial buddy.\n"
        )
        context += json.dumps(repayment_data, indent=2)

        prompt_text = (
            f"{context}\n\n"
            f"The user has asked:\n\"{prompt}\"\n\n"
            f"Based on the above data, suggest the best repayment strategy (Snowball vs Avalanche), show payoff timelines per account, "
            f"and give 2 friendly tips to manage credit stress."
        )
        prompt_text += (
            "\n\n---\n"
            "Formatting Instructions:\n"
            "- Keep response short and structured.\n"
            "- Use bullet points where possible.\n"
            "- Bold key figures (e.g., **Monthly Surplus**: ₹2.05L).\n"
            "- Avoid long paragraphs or repeating data.\n"
            "- End with a 1-line friendly recommendation or encouragement."
        )

        response = model.generate_content(prompt_text)
        if not hasattr(response, 'text') or not response.text:
            raise ValueError("Gemini returned no text response.")
        return {"text": response.text.strip(), "raw_prompt": prompt_text}
    except Exception as e:
        logging.exception("[askrepay] Error generating repayment advice:")
        return {"text": f"Error generating repayment advice: {str(e)}"}


# Buying agent function
def askbuy(prompt: str, buying_data: dict) -> str:
    try:
        context = (
            "You are a Buying Agent — a smart financial assistant that helps users decide if they can afford something. "
            "Use the structured financial data below to evaluate the user's financial readiness, compare EMI vs. upfront payment, "
            "and suggest if they should proceed with the purchase. Be practical and friendly like a financial buddy.\n"
        )
        context += json.dumps(buying_data, indent=2)

        prompt_text = (
            f"{context}\n\n"
            f"The user has asked:\n\"{prompt}\"\n\n"
            f"Based on the above data, provide a short summary of their readiness to buy this item. "
            f"If EMI is needed, mention approximate safe EMI threshold. Suggest 2 tips for smart buying."
        )
        prompt_text += (
            "\n\n---\n"
            "The user has asked:\n\"{prompt}\"\n\n"
            "Analyze their credit data and recommend a repayment path:\n"
            "1. Financial Readiness Check\n"
            "2. Affordability (% of surplus used)\n"
            "3. Best method (Snowball or Avalanche)\n"
            "4. Debt payoff timeline (per account if possible)\n"
            "5. Debt stress tips (budgeting or buffers)\n\n"
            "Be concise, highlight ₹ & %, and close with a supportive nudge."
        )

        response = model.generate_content(prompt_text)
        if not hasattr(response, 'text') or not response.text:
            raise ValueError("Gemini returned no text response.")
        return {"text": response.text.strip(), "raw_prompt": prompt_text}
    except Exception as e:
        logging.exception("[askbuy] Error generating buying advice:")
        return {"text": f"Error generating buying advice: {str(e)}"}


# Goal extraction utility

def extract_goal(prompt: str):
    """
    Extract goal type and amount from a user's financial planning prompt.
    Returns a dictionary like: {"goal_type": "car", "amount": 500000, "timeline_months": 12}
    """
    try:
        # Find ₹ amount
        amount_match = re.search(r"₹\s?([\d,]+)", prompt)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else None

        # Find time duration (in months or years)
        timeline_match = re.search(r"in (\d+)\s*(months?|years?)", prompt, re.IGNORECASE)
        timeline = None
        if timeline_match:
            value = int(timeline_match.group(1))
            unit = timeline_match.group(2).lower()
            timeline = value * 12 if "year" in unit else value

        # Guess goal type from common keywords
        goal_keywords = ["wedding", "vacation", "car", "bike", "home", "education", "retirement", "sabbatical"]
        goal_type = None
        for word in goal_keywords:
            if word in prompt.lower():
                goal_type = word
                break

        return {"goal_type": goal_type, "amount": amount, "timeline_months": timeline}
    except Exception as e:
        print("[extract_goal] Error:", e)
        return {}