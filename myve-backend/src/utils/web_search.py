import os
import re
import json
import requests
import textwrap
from typing import List, Dict
from src.services.gemini_service import call_gemini

# --- Data Fetching Functions (Google, Reddit, Perplexity) ---

GOOGLE_API_KEY = "your_google_api_key"
GOOGLE_CSE_ID = "your_custom_search_engine_id"
REDDIT_BASE_URL = "https://www.reddit.com/search.json"

def google_product_lookup(query: str) -> List[dict]:
    """Fetch product search results from Google Custom Search API."""
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
    }
    response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
    results = []
    if response.status_code == 200:
        items = response.json().get("items", [])
        for item in items[:3]:
            results.append({
                "title": item.get("title"),
                "price": extract_price(item.get("snippet", "")),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "source": "Google Search"
            })
    return results or [{"error": "No results found in Google Search"}]

def reddit_buying_threads(item: str) -> List[dict]:
    """Search Reddit for buying-related threads about the item."""
    headers = {"User-Agent": "myve-agent/0.1"}
    params = {"q": f"buy {item}", "sort": "relevance", "limit": 5}
    response = requests.get(REDDIT_BASE_URL, headers=headers, params=params)
    results = []
    if response.status_code == 200:
        posts = response.json().get("data", {}).get("children", [])
        for post in posts:
            data = post.get("data", {})
            results.append({
                "title": data.get("title"),
                "url": f"https://www.reddit.com{data.get('permalink')}",
                "score": data.get("score"),
                "subreddit": data.get("subreddit"),
                "source": "Reddit"
            })
    return results

def fetch_perplexity_insights(prompt: str) -> str:
    """Fetch concise real-world buying advice from Perplexity AI API with streaming support."""
    try:
        response = requests.post(
            url="https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ.get('PERPLEXITY_API_KEY', 'your_default_key_here')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar-pro",
                "stream": True,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            stream=True,
            timeout=20
        )

        if response.status_code != 200:
            return f"(Perplexity Streaming API error: {response.status_code})"

        full_reply = ""
        for line in response.iter_lines():
            if line:
                if line.startswith(b'data: '):
                    try:
                        chunk = json.loads(line[len(b'data: '):])
                        content_piece = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content_piece:
                            full_reply += content_piece
                    except Exception:
                        continue
        return full_reply.strip() if full_reply else "(No content from streaming response)"
    except Exception as e:
        # Fallback to original non-streaming behavior or return error
        try:
            response = requests.post(
                url="https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.environ.get('PERPLEXITY_API_KEY', 'your_default_key_here')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"(Perplexity API error: {response.status_code})"
        except Exception as e2:
            return f"(Perplexity Streaming Error: {str(e)})"

# --- Utility Functions (parsing, price extraction) ---

def extract_price(snippet: str) -> str:
    """Extract price string from a text snippet."""
    patterns = [r'₹[\d,.]+', r'Rs\.?\s?[\d,.]+[kK]?', r'INR\s?[\d,.]+']
    for pattern in patterns:
        match = re.search(pattern, snippet)
        if match:
            return match.group(0)
    return None

def parse_price_to_float(price_str):
    """Convert a price string to a float, stripping non-numeric characters."""
    try:
        if isinstance(price_str, str):
            cleaned = re.sub(r"[^\d.]", "", price_str.replace(",", ""))
            return float(cleaned)
    except Exception:
        return None
    return None

# --- Insight Extraction (Reddit summarization and LLM synthesis) ---

def extract_buying_insight_from_reddit(prompt: str, threads: List[dict]) -> str:
    """Summarize smart buying advice from Reddit threads using Gemini LLM."""
    context = "\n\n".join([f"{post['title']}\n{post['url']}" for post in threads])
    full_prompt = f"""
You are a financial assistant. The user wants to buy: {prompt}.

Based on these Reddit discussions, extract smart buying advice, deal tips, and community hacks:
{context}

Summarize 3-5 practical buying tips in bullet points.
"""
    try:
        return call_gemini(full_prompt, temperature=0.7)
    except Exception as e:
        return f"(Insight fetch failed: {str(e)})"

# --- Main Aggregator Function ---

def fetch_realworld_buying_info(item_category: str, prompt: str) -> dict:
    """
    Aggregate product buying insights from Google, Reddit, and Perplexity,
    and synthesize a combined summary using Gemini LLM.
    """
    google_results = google_product_lookup(prompt)
    reddit_results = reddit_buying_threads(item_category)
    community_advice = extract_buying_insight_from_reddit(prompt, reddit_results)

    ppx_prompt = f"""
        The user is considering a purchase related to: "{prompt}" — likely for wedding gifting or ceremonial use if relevant.
        Please extract real-world buying advice, deals, prices, current rates, and making charges (range in %) if it involves jewelry.
        Format your response concisely in this structure:
        ---
        • Price (if mentioned): ₹XXX
        • Best source to buy (Amazon/Flipkart/etc)
        • Any EMI or deal available
        • 2-3 smart tips or community hacks
        ---
        This is for a user based in Bangalore, India. No fluff, just facts.
        """
    ppx_insight = fetch_perplexity_insights(ppx_prompt)
    if ppx_insight and "401" in ppx_insight:
        ppx_insight = "(Perplexity access unauthorized – check API key or token)"

    estimated_price = None
    source = "N/A"
    for g in google_results:
        price_str = g.get("price")
        if isinstance(g, dict) and price_str:
            parsed_price = parse_price_to_float(price_str)
            if parsed_price:
                estimated_price = parsed_price
                source = g["source"]
                break

    if not estimated_price:
        price_match = re.search(r'₹[\d,]+', ppx_insight or "")
        if price_match:
            estimated_price = float(price_match.group(0).replace('₹', '').replace(',', '').strip())
            source = "Perplexity"
        else:
            estimated_price = None
            source = "N/A"

    try:
        top_google_results = "\n".join(
            [f"{g.get('title', '')}: {g.get('snippet', '')}" for g in google_results[:3]]
        )
        full_prompt = (
            f"The user wants to buy: \"{prompt}\".\n\n"
            f"Here is some context:\n"
            f"Google results:\n{top_google_results}\n\n"
            f"Reddit insights:\n{community_advice}\n\n"
            f"Perplexity tip:\n{ppx_insight}\n\n"
            f"Summarize smart, fact-based buying advice tailored to this product or service. Use short crisp bullet points."
        )
        combined_llm_advice = call_gemini(full_prompt, temperature=0.7)
    except Exception as e:
        combined_llm_advice = f"(Failed to generate combined advice: {str(e)})"

    combined_advice = textwrap.shorten(combined_llm_advice.strip(), width=700, placeholder="...")
    # Gold-specific tip if making charge not present
    if item_category == "gold" and combined_advice and "making charge" not in combined_advice.lower():
        combined_advice += "\n• Always compare making charges — they typically range from 3% to 25% depending on jeweller and item."

    return {
        "google_results": google_results if not (len(google_results) == 1 and "error" in google_results[0]) else [],
        "reddit_threads": reddit_results,
        "title": google_results[0].get("title", "Unknown") if google_results else "Unknown",
        "price": estimated_price,
        "source": source,
        "extra_info": f"Reddit has {len(reddit_results)} discussions about {item_category}.",
        "community_advice": community_advice.strip(),
        "perplexity_advice": textwrap.shorten(ppx_insight.strip(), width=700, placeholder="...") if ppx_insight else "",
        "combined_advice": combined_advice
    }

def fetch_product_insights(prompt: str, category: str, user_location: str = "India") -> dict:
    """
    Legacy function to fetch product insights combining Google, Reddit, and Perplexity results.
    """
    google_results = google_product_lookup(f"{prompt} in {user_location}")
    reddit_results = reddit_buying_threads(prompt)
    community_advice = extract_buying_insight_from_reddit(prompt, reddit_results)
    perplexity_prompt = f"""
    Please extract real-world buying advice, deals, prices, and current offers for: "{prompt}".
    Format your response concisely in this structure:
    ---
    • Price (if mentioned): ₹XXX
    • Best source to buy
    • Any EMI or deal available
    • 2-3 smart tips or community hacks
    ---
    This is for a user based in {user_location}. No fluff, just facts.
    """
    ppx_insight = fetch_perplexity_insights(perplexity_prompt)

    estimated_price = None
    source = "N/A"
    for g in google_results:
        price_str = g.get("price")
        if price_str:
            parsed_price = parse_price_to_float(price_str)
            if parsed_price:
                estimated_price = parsed_price
                source = g["source"]
                break

    if not estimated_price:
        price_match = re.search(r'₹[\d,]+', ppx_insight or "")
        if price_match:
            estimated_price = float(price_match.group(0).replace('₹', '').replace(',', '').strip())
            source = "Perplexity"

    try:
        top_google_results = "\n".join(
            [f"{g.get('title', '')}: {g.get('snippet', '')}" for g in google_results[:3]]
        )
        full_prompt = (
            f"The user wants to buy: \"{prompt}\".\n\n"
            f"Google results:\n{top_google_results}\n\n"
            f"Reddit:\n{community_advice}\n\n"
            f"Perplexity:\n{ppx_insight}\n\n"
            f"Summarize smart, fact-based buying advice tailored to this product or service. Use short crisp bullet points."
        )
        combined_advice = call_gemini(full_prompt, temperature=0.7)
    except Exception as e:
        combined_advice = f"(LLM summarization failed: {str(e)})"

    return {
        "google_results": google_results,
        "reddit_threads": reddit_results,
        "title": google_results[0].get("title", "Unknown") if google_results else "Unknown",
        "price": estimated_price,
        "source": source,
        "extra_info": f"Reddit has {len(reddit_results)} discussions about this product.",
        "community_advice": community_advice.strip(),
        "perplexity_advice": textwrap.shorten(ppx_insight.strip(), width=700, placeholder="..."),
        "combined_advice": textwrap.shorten(combined_advice.strip(), width=700, placeholder="...")
    }

# --- Batch Testing ---

def run_perplexity_tests():
    """Run batch tests for Perplexity AI insights on multiple queries."""
    test_items = [
        "macbook m4 price in India",
        "iPhone 16 release and best deals",
        "22k gold chain price in Bangalore",
        "Tata Nexon 2025 on-road price in Bangalore",
        "botox treatment cost at Kaya Clinic",
        "best air conditioner under ₹50000",
        "samsung fridge double door price",
        "Apple Vision Pro India launch price",
        "diamond ring Malabar Gold current rate",
        "home inverter price for 3BHK"
    ]

    for query in test_items:
        print("="*60)
        print(f"🔍 Query: {query}")
        result = fetch_perplexity_insights(f"""
        Please extract real-world buying advice, deals, prices, and current offers for: "{query}".
        Format your response concisely in this structure:
        ---
        • Price (if mentioned): ₹XXX
        • Best source to buy (Amazon/Flipkart/etc)
        • Any EMI or deal available
        • 2-3 smart tips or community hacks
        ---
        This is for a user based in Bangalore, India. No fluff, just facts.
        """)
        print(result)
        print("="*60)

if __name__ == "__main__":
    run_perplexity_tests()
# --- Product Summary Formatter ---

def render_product_summary(product_data: dict) -> str:
    summary = f"""📦 Item: {product_data.get('title', 'Unknown')}
💸 Price: """
    price_val = product_data.get('price', 0)
    try:
        price_val = float(price_val)
    except Exception:
        price_val = 0
    if price_val > 0:
        summary += f"₹{int(price_val):,}"
    else:
        summary += "Not found"
    summary += f" ({product_data.get('source', 'N/A')})"
    if product_data.get('extra_info'):
        summary += f"\n{product_data.get('extra_info', '')}"

    if product_data.get("community_advice"):
        tips = [tip.strip() for tip in product_data["community_advice"].split("\n") if tip.strip()]
        top_tips = "\n".join([f"• {tip}" for tip in tips[:3]])
        if top_tips:
            summary += f"\n👥 Reddit Tips:\n{top_tips}"
    if product_data.get("perplexity_advice"):
        tip_lines = [line for line in product_data['perplexity_advice'].splitlines() if line.strip()]
        trimmed_tip = "\n".join(tip_lines[:4])
        if trimmed_tip:
            summary += f"\n💡 Perplexity Tip:\n{trimmed_tip}"
    if product_data.get("combined_advice"):
        summary += f"\n🧠 Final Smart Tips:\n{product_data['combined_advice']}"
    return summary


# --- Perplexity Planning Insight ---
def fetch_perplexity_planning_insight(prompt: str) -> str:
    """Fetch planning-related financial advice using a focused Perplexity prompt."""
    return fetch_perplexity_insights(
        f"Give a structured financial roadmap for: {prompt}. Focus on SIPs, ETFs, direct stocks, monthly investing strategy. Format with numbered sections and bold amounts."
    )