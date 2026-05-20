CURRENCY_PAIRS = ["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"]

BANKS = ["中国银行", "招商银行", "宁波银行", "杭州银行"]

BANK_SPREADS = {
    "中国银行": {"bid_offset": -0.0020, "ask_offset": 0.0020},
    "招商银行": {"bid_offset": -0.0015, "ask_offset": 0.0015},
    "宁波银行": {"bid_offset": -0.0010, "ask_offset": 0.0010},
    "杭州银行": {"bid_offset": -0.0018, "ask_offset": 0.0018},
}

API_URLS = {
    "exchangerate-api": "https://api.exchangerate-api.com/v4/latest/USD",
    "openexchangerates": "https://open.er-api.com/v6/latest/USD",
}

FETCH_INTERVAL_SECONDS = 60
DB_PATH = "forex_data.db"
