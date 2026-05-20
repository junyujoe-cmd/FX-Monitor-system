import requests
from config import CURRENCY_PAIRS


def fetch_exchangerate_api():
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/CNY", timeout=10)
        data = resp.json()
        rates = data.get("rates", {})
        return {
            "USDCNY": {"bid": None, "ask": None, "mid": round(1 / rates["USD"], 4)},
            "EURCNY": {"bid": None, "ask": None, "mid": round(1 / rates["EUR"], 4)},
            "HKDCNY": {"bid": None, "ask": None, "mid": round(1 / rates["HKD"], 4)},
            "JPYCNY": {"bid": None, "ask": None, "mid": round(1 / rates["JPY"], 6)},
        }
    except Exception as e:
        print(f"API fetch error: {e}")
        return None


def fetch_all_quotes():
    result = fetch_exchangerate_api()
    if result:
        return result
    print("All data sources failed")
    return None
