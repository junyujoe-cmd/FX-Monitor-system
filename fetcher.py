import akshare as ak


def fetch_market_quotes():
    """从中国外汇交易中心(CFETS)获取人民币外汇即期买卖报价"""
    try:
        df = ak.fx_spot_quote()
        pair_map = {
            "USD/CNY": "USDCNY",
            "EUR/CNY": "EURCNY",
            "HKD/CNY": "HKDCNY",
            "100JPY/CNY": "JPYCNY",
        }
        result = {}
        for _, row in df.iterrows():
            pair = row["货币对"]
            if pair in pair_map:
                bid = float(row["买报价"])
                ask = float(row["卖报价"])
                mid = round((bid + ask) / 2, 4)
                result[pair_map[pair]] = {"bid": round(bid, 4), "ask": round(ask, 4), "mid": mid}
        return result if result else None
    except Exception as e:
        print(f"CFETS fetch error: {e}")
        return None


def fetch_all_quotes():
    result = fetch_market_quotes()
    if result:
        return result
    print("All data sources failed")
    return None
