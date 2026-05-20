import requests
from bs4 import BeautifulSoup


def fetch_boc_rates():
    """从中国银行官网抓取实时外汇牌价"""
    try:
        resp = requests.get("https://www.boc.cn/sourcedb/whpj/", timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "priceTable"})
        if not table:
            return None

        name_map = {
            "美元": "USDCNY",
            "港币": "HKDCNY",
            "欧元": "EURCNY",
            "日元": "JPYCNY",
        }

        result = {}
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 6:
                name = cells[0].text.strip()
                if name in name_map:
                    buy_str = cells[1].text.strip()
                    sell_str = cells[3].text.strip()
                    mid_str = cells[5].text.strip()
                    if buy_str and sell_str and mid_str:
                        pair = name_map[name]
                        buy_per_100 = float(buy_str)
                        sell_per_100 = float(sell_str)
                        mid_per_100 = float(mid_str)
                        result[pair] = {
                            "bid": round(buy_per_100 / 100, 4),
                            "ask": round(sell_per_100 / 100, 4),
                            "mid": round(mid_per_100 / 100, 4),
                        }
        return result if result else None
    except Exception as e:
        print(f"BOC fetch error: {e}")
        return None


def fetch_cmb_rates():
    """从招商银行API获取实时外汇牌价"""
    try:
        url = "https://fx.cmbchina.com/api/v1/fx/rate"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://fx.cmbchina.com/",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if data.get("returnCode") != "SUC0000":
            return None

        name_map = {
            "美元": "USDCNY",
            "港币": "HKDCNY",
            "欧元": "EURCNY",
            "日元": "JPYCNY",
        }

        result = {}
        for item in data.get("body", []):
            name = item.get("ccyNbr", "")
            if name in name_map:
                buy_str = item.get("rtbBid", "")
                sell_str = item.get("rthOfr", "")
                if buy_str and sell_str:
                    pair = name_map[name]
                    buy_val = float(buy_str) / 100
                    sell_val = float(sell_str) / 100
                    result[pair] = {
                        "bid": round(buy_val, 4),
                        "ask": round(sell_val, 4),
                        "mid": round((buy_val + sell_val) / 2, 4),
                    }
        return result if result else None
    except Exception as e:
        print(f"CMB fetch error: {e}")
        return None
