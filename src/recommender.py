import pandas as pd
from src.agents import risk_profile_agent, amount_filter_agent
from src.historical_nav import compute_all_returns


# ---------------- FUND TYPE DETECTION ----------------
def detect_fund_type(name: str) -> str:
    name = str(name).lower()

    # GOLD
    if any(k in name for k in ["gold", "gold etf", "etf gold"]):
        return "Gold"

    # DEBT
    if any(k in name for k in [
        "debt", "bond", "gilt", "liquid", "overnight", "money market",
        "ultra short", "short duration", "medium duration", "long duration",
        "corporate bond", "banking", "psu", "dynamic bond",
        "credit risk", "income", "floater"
    ]):
        return "Debt"

    # EQUITY
    if any(k in name for k in [
        "equity", "mid cap", "small cap", "large cap",
        "flexi cap", "multi cap", "elss", "value", "contra",
        "focused", "bluechip", "dividend yield", "index fund",
        "nifty", "sensex", "top 100", "top 50"
    ]):
        return "Equity"

    # HYBRID
    if any(k in name for k in [
        "balanced", "hybrid", "aggressive hybrid", "conservative hybrid"
    ]):
        return "Hybrid"

    return "Other"


# ---------------- RISK FILTER ----------------
def filter_by_risk(df, user_type):
    if user_type == "Conservative":
        return df[df["fund_type"].isin(["Debt", "Hybrid", "Gold"])]
    elif user_type == "Balanced":
        return df[df["fund_type"].isin(["Hybrid", "Equity", "Debt"])]
    else:
        return df[df["fund_type"].isin(["Equity", "Hybrid"])]


# ---------------- MAIN AGENTIC RECOMMENDER ----------------
def agentic_recommender(
    df_master,
    risk_appetite,
    horizon,
    invest_type,
    amount,
    fund_type,
    top_n=5
):
    # 1) Risk profile agent
    user_type = risk_profile_agent(risk_appetite, horizon)

    df_master = df_master.copy()

    # 2) Ensure scheme_code exists
    if "scheme_code" not in df_master.columns:
        raise Exception("❌ scheme_code column missing in df_master. Check merge_hist_live() output.")

    # 3) Detect name column
    if "scheme_name" in df_master.columns:
        name_col = "scheme_name"
    elif "fund_name" in df_master.columns:
        name_col = "fund_name"
    else:
        raise Exception("❌ No scheme_name or fund_name column found!")

    # 4) Always create fund_type column
    df_master["fund_type"] = df_master[name_col].apply(detect_fund_type)

    # normalize
    df_master["fund_type"] = df_master["fund_type"].astype(str).str.strip().str.title()
    fund_type = str(fund_type).strip().title()

    # 5) Filter by user selected fund type
    df_master = df_master[df_master["fund_type"] == fund_type]

    if df_master.empty:
        return pd.DataFrame(), [f"⚠️ No funds found for selected Fund Type: {fund_type}"]

    # 6) Amount filter agent
    filtered = amount_filter_agent(df_master, invest_type, amount)

    if filtered.empty:
        return pd.DataFrame(), ["⚠️ No funds found after amount filter. Try changing amount/type."]

    # 7) Risk filtering
    filtered = filter_by_risk(filtered, user_type)

    if filtered.empty:
        return pd.DataFrame(), ["⚠️ No funds found after risk filtering. Try different risk/horizon."]

    # 8) Drop invalid rows
    filtered["nav_change_pct"] = pd.to_numeric(filtered.get("nav_change_pct"), errors="coerce")
    filtered["nav"] = pd.to_numeric(filtered.get("nav"), errors="coerce")

    filtered = filtered.dropna(subset=["nav_change_pct", "nav"])

    if filtered.empty:
        return pd.DataFrame(), ["⚠️ No valid NAV rows found after cleaning."]

    # 9) Initial scoring (fast ranking)
    filtered["score_initial"] = (0.8 * filtered["nav_change_pct"]) + (0.2 * filtered["nav"])
    top_candidates = filtered.sort_values("score_initial", ascending=False).head(10)

    # 10) Agentic tool call -> compute historical returns
    returns_list = []

    for _, row in top_candidates.iterrows():
        scheme_code = str(row["scheme_code"]).strip()

        try:
            ret = compute_all_returns(scheme_code)  # must return dict with returns_6m, returns_1y etc
        except Exception:
            ret = {
                "returns_6m": None,
                "returns_1y": None,
                "returns_2y": None,
                "returns_3y": None,
                "returns_5y": None,
                "returns_10y": None,
            }

        ret["scheme_code"] = scheme_code
        returns_list.append(ret)

    df_returns = pd.DataFrame(returns_list)

    # 11) Merge returns back
    top_candidates["scheme_code"] = top_candidates["scheme_code"].astype(str).str.strip()
    df_returns["scheme_code"] = df_returns["scheme_code"].astype(str).str.strip()

    top_candidates = top_candidates.merge(df_returns, on="scheme_code", how="left")

    # 12) Final score (long-term + short-term)
    for c in ["returns_6m", "returns_1y", "returns_2y", "returns_3y", "returns_5y", "returns_10y"]:
        if c not in top_candidates.columns:
            top_candidates[c] = None
        top_candidates[c] = pd.to_numeric(top_candidates[c], errors="coerce")

    top_candidates["final_score"] = (
        0.25 * top_candidates["returns_1y"].fillna(0) +
        0.20 * top_candidates["returns_3y"].fillna(0) +
        0.20 * top_candidates["returns_5y"].fillna(0) +
        0.10 * top_candidates["returns_10y"].fillna(0) +
        0.25 * top_candidates["nav_change_pct"].fillna(0)
    )

    # 13) Top funds output
    top_funds = top_candidates.sort_values("final_score", ascending=False).head(top_n)

    # 14) Explanations (fixed string formatting)
    explanations = []
    for _, row in top_funds.iterrows():
        explanations.append(
            f"✅ {row.get(name_col, 'Unknown Fund')} ({row['fund_type']}) selected.\n"
            f"📌 6M: {row.get('returns_6m', 0)} | "
            f"1Y: {row.get('returns_1y', 0)} | "
            f"2Y: {row.get('returns_2y', 0)} | "
            f"3Y: {row.get('returns_3y', 0)} | "
            f"5Y: {row.get('returns_5y', 0)} | "
            f"10Y: {row.get('returns_10y', 0)}\n"
            f"📈 NAV Change: {row['nav_change_pct']:.2f}% | Final Score: {row['final_score']:.2f}\n"
            f"🧠 Profile Match: {user_type}"
        )

    return top_funds, explanations
