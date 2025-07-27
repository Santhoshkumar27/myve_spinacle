import logging
from src.services import mcp_client
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["myve_db"]

async def fetch_with_fallback(collection, mobile_number, projection, fallback_fn, force_refresh=False):
    if not force_refresh:
        doc = db[collection].find_one({"mobile_number": mobile_number}, projection)
        if doc and "data" in doc:
            return doc["data"]
    result = await fallback_fn(mobile_number)
    db[collection].update_one(
        {"mobile_number": mobile_number},
        {"$set": {"data": result}},
        upsert=True
    )
    return result


# --- MongoDB upsert and fetch helpers for each data type ---
def upsert_networth(mobile_number, result):
    db.networth.update_one(
        {"mobile_number": mobile_number},
        {"$set": {"data": result}},
        upsert=True
    )

def upsert_credit(mobile_number, result):
    db.credit.update_one(
        {"mobile_number": mobile_number},
        {"$set": {"data": result}},
        upsert=True
    )

def upsert_assets(mobile_number, result):
    db.assets.update_one(
        {"mobile_number": mobile_number},
        {"$set": {"data": result}},
        upsert=True
    )

def upsert_mf_transactions(mobile_number, result):
    db.mf_transactions.update_one(
        {"mobile_number": mobile_number},
        {"$set": {"data": result}},
        upsert=True
    )

def upsert_bank_transactions(mobile_number, result):
    db.bank_transactions.update_one(
        {"mobile_number": mobile_number},
        {"$set": {"data": result}},
        upsert=True
    )

def upsert_stock_transactions(mobile_number, result):
    db.stock_transactions.update_one(
        {"mobile_number": mobile_number},
        {"$set": {"data": result}},
        upsert=True
    )

# --- Retrieval functions: check Mongo first, then fetch from mcp_client, then cache ---
async def fetch_networth(mobile_number, force_refresh=False):
    data = await fetch_with_fallback(
        "networth",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_networth,
        force_refresh
    )
    # 🔥 Fix: unwrap "data" if wrapped
    if "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if isinstance(data, dict):
        data["creditReport"] = data.get("creditReport", {})
        data["bankTransactions"] = data.get("bankTransactions", {}).get("transactions", [])
        data["mfTransactions"] = data.get("mfTransactions", {}).get("transactions", [])
        data["stocks"] = data.get("stocks", {}).get("stockTransactions", [])
        data["assets"] = data.get("assets", []) if isinstance(data.get("assets"), list) else []
    return data if isinstance(data, dict) else {
        "netWorth": { "currencyCode": "INR", "units": 0 },
        "assets": [],
        "accounts": {},
        "liabilities": []
    }

async def fetch_credit(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "credit",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_credit,
        force_refresh
    )

async def fetch_assets(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "assets",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_assets,
        force_refresh
    )

async def fetch_mf_transactions(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "mf_transactions",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_mf_transactions,
        force_refresh
    )

async def fetch_bank_transactions(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "bank_transactions",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_bank_transactions,
        force_refresh
    )

async def fetch_stock_transactions(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "stock_transactions",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_stock_transactions,
        force_refresh
    )





async def fetch_mcp_context(mobile_number):
    context_parts = []
    context_parts.append("## User Financial Overview")
    try:
        try:
            net = await fetch_networth(mobile_number)
        except Exception as e:
            net = {}
            logging.warning(f"[WARN] Could not fetch networth for {mobile_number}: {e}")

        try:
            credit = await fetch_credit(mobile_number)
        except Exception as e:
            credit = []
            logging.warning(f"[WARN] Could not fetch credit data for {mobile_number}: {e}")

        try:
            assets = await fetch_assets(mobile_number)
        except Exception as e:
            assets = []
            logging.warning(f"[WARN] Could not fetch assets for {mobile_number}: {e}")

        try:
            mf_txns = await fetch_mf_transactions(mobile_number)
        except Exception as e:
            mf_txns = []
            logging.warning(f"[WARN] Could not fetch mutual fund transactions: {e}")

        try:
            bank_txns = await fetch_bank_transactions(mobile_number)
        except Exception as e:
            bank_txns = []
            logging.warning(f"[WARN] Could not fetch bank transactions: {e}")

        try:
            stock_txns = await fetch_stock_transactions(mobile_number)
        except Exception as e:
            stock_txns = []
            logging.warning(f"[WARN] Could not fetch stock transactions: {e}")

        # Optionally, structure and upsert combined transactions for analytics (legacy)
        # ... (omitted for brevity, see previous implementation if needed)

        context_parts.append("**Note:** Further implementation will format and return all context segments for LLM consumption.")

        logging.info(f"[CONTEXT] Final assembled user context for {mobile_number}:\n" + "\n".join(context_parts))
        return "\n".join(context_parts)
    except Exception as e:
        logging.exception(f"[ERROR] Unexpected error in fetch_mcp_context for {mobile_number}: {e}")
        raise

# --- Monthly Trend retrieval and upsert ---
async def fetch_monthly_trend(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "monthly_trend",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_monthly_trend,
        force_refresh
    )


# --- EPF Details retrieval and upsert ---
async def fetch_epf_details(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "epf_details",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_epf_details,
        force_refresh
    )

# --- Loan Status retrieval and upsert ---
async def fetch_loan_status(mobile_number, force_refresh=False):
    return await fetch_with_fallback(
        "loan_status",
        mobile_number,
        {"data": 1},
        mcp_client.fetch_loan_status,
        force_refresh
    )