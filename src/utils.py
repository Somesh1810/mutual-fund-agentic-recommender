def classify_fund_type(name: str):
    n = str(name).lower()

    if "gold" in n or "etf" in n:
        return "Gold"

    debt_keywords = ["debt", "bond", "liquid", "overnight", "gilt", "duration", "psu", "income"]
    if any(k in n for k in debt_keywords):
        return "Debt"

    return "Equity"
