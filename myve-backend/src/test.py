import json
import os

MOBILE_NUMBER = "2222222222"
SESSION_ID = "myve"

# Update this path to wherever `fi-mcp-dev-master` lives
TEST_DATA_PATH = f"/Users/santhoshkumar/Downloads/fi-mcp-dev-master/test_data_dir/{MOBILE_NUMBER}/fetch_net_worth.json"

def guide_user_login():
    login_url = f"http://localhost:8080/mockWebPage?sessionId={SESSION_ID}"
    print("\n== MCP Login ==")
    print("Please open this URL in your browser and login manually:")
    print(login_url)
    input("Press Enter after completing login...")

def fetch_mock_data():
    print("\nReading mock net worth data...")
    try:
        with open(TEST_DATA_PATH, "r") as file:
            data = json.load(file)
            print("✅ Net Worth Data:\n")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"❌ Error reading mock data: {e}")

if __name__ == "__main__":
    guide_user_login()
    fetch_mock_data()