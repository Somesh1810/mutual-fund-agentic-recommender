import re
import pandas as pd
import streamlit as st

from src.data_fetch import fetch_live_nav
from src.charts import plot_returns_chart, plot_compare_returns


# ================= LOAD FUND PROFILES =================
def load_fund_profiles(path="data/fund_profiles.csv"):
    try:
        df = pd.read_csv(path)
        return df if "fund_name" in df.columns else None
    except Exception:
        return None


# ================= CLEAN USER QUERY =================
def clean_query(text: str) -> str:
    text = text.lower()

    remove_words = [
        "nav", "return", "returns", "risk",
        "details", "tell", "me", "about",
        "show", "what", "is", "fund",
        "direct", "regular", "plan", "option",
        "compare", "vs", "with", "of"
    ]

    for w in remove_words:
        text = re.sub(rf"\b{w}\b", "", text)

    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ================= WORD MATCH =================
def _word_match(df, keyword):
    if not keyword:
        return pd.DataFrame()

    words = keyword.split()
    mask = pd.Series(True, index=df.index)

    for w in words:
        mask &= df["fund_name"].str.lower().str.contains(w, na=False)

    return df[mask]


# ================= FIND MATCH =================
def find_best_match(df, keyword):
    match = _word_match(df, keyword)

    if match.empty:
        return None
    if len(match) == 1:
        return match.iloc[0]

    return match


# ================= SELECT BEST SCHEME =================
def select_best_scheme(df):
    priority = ["direct plan growth", "direct growth", "growth"]

    for p in priority:
        m = df[df["fund_name"].str.lower().str.contains(p, na=False)]
        if not m.empty:
            return m.iloc[0]

    return df.iloc[0]


# ================= LIVE NAV FALLBACK =================
def fetch_from_live_amfi(keyword):
    df = fetch_live_nav()
    match = _word_match(df, keyword)
    return None if match.empty else match.iloc[0]


# ================= MAIN QA FUNCTION =================
def answer_fund_question(question: str, df_profiles: pd.DataFrame):

    # -------- SESSION MEMORY --------
    st.session_state.setdefault("base_fund", None)
    st.session_state.setdefault("compare_fund", None)

    q = question.lower()
    keyword = clean_query(question)

    # -------- FIND FUND --------
    fund_row = None
    match = find_best_match(df_profiles, keyword)

    if isinstance(match, pd.DataFrame):
        fund_row = select_best_scheme(match)
    elif isinstance(match, pd.Series):
        fund_row = match

    # Use memory only if user didn’t type fund
    if fund_row is None and not keyword:
        fund_row = st.session_state["base_fund"]

    if fund_row is None and keyword:
        fund_row = fetch_from_live_amfi(keyword)

    # ==================================================
    # 🔹 CAPTURE COMPARISON FUND
    # ==================================================
    if "compare" in q and fund_row is not None:
        if st.session_state["base_fund"] is None:
            st.session_state["base_fund"] = fund_row
            return (
                f"✅ Base fund selected:\n\n"
                f"• **{fund_row['fund_name']}**\n\n"
                f"👉 Now type: `compare with <fund name>`"
            )

        st.session_state["compare_fund"] = fund_row
        return (
            f"🔄 **Comparison Ready**\n\n"
            f"🔹 Fund 1: {st.session_state['base_fund']['fund_name']}\n"
            f"🔹 Fund 2: {fund_row['fund_name']}\n\n"
            f"👉 Ask: **compare nav | compare returns**"
        )

    # ==================================================
    # 🔹 COMPARE RETURNS
    # ==================================================
    if "compare returns" in q:
        f1 = st.session_state["base_fund"]
        f2 = st.session_state["compare_fund"]

        if f1 is None or f2 is None:
            return "⚠️ Please select two funds first using `compare with <fund>`."

        plot_compare_returns(f1, f2)

        return (
            f"📊 **Return Comparison**\n\n"
            f"🔹 {f1['fund_name']}\n"
            f"• 1Y: {f1.get('returns_1y', 'N/A')}%\n"
            f"• 3Y: {f1.get('returns_3y', 'N/A')}%\n"
            f"• 5Y: {f1.get('returns_5y', 'N/A')}%\n\n"
            f"🔹 {f2['fund_name']}\n"
            f"• 1Y: {f2.get('returns_1y', 'N/A')}%\n"
            f"• 3Y: {f2.get('returns_3y', 'N/A')}%\n"
            f"• 5Y: {f2.get('returns_5y', 'N/A')}%"
        )

    # ==================================================
    # 🔹 SINGLE FUND QUERIES
    # ==================================================
    if fund_row is None:
        return "❌ I couldn't find that fund. Please type a clearer fund name."

    if "nav" in q:
        st.session_state["base_fund"] = fund_row
        return f"💰 **NAV of {fund_row['fund_name']}** is **{fund_row.get('nav', 'N/A')}**"

    if ("return" in q or "returns" in q) and "compare" not in q:
        st.session_state["base_fund"] = fund_row

        # 🔹 Chart inside clean container
        with st.container():
            plot_returns_chart(
                fund_row,
                title=f"Returns – {fund_row['fund_name']}"
            )

        return (
            f"📈 **Returns – {fund_row['fund_name']}**\n\n"
            f"• 1Y: {fund_row.get('returns_1y', 'N/A')}%\n"
            f"• 3Y: {fund_row.get('returns_3y', 'N/A')}%\n"
            f"• 5Y: {fund_row.get('returns_5y', 'N/A')}%"
        )

    if "risk" in q:
        st.session_state["base_fund"] = fund_row
        return (
            f"⚠️ **Risk Profile**\n\n"
            f"• Fund Type: {fund_row.get('fund_type', 'Unknown')}\n"
            f"• Equity → High volatility\n"
            f"• Debt → Lower volatility\n"
            f"• Hybrid → Moderate risk"
        )

    # ==================================================
    # 🔹 SUMMARY
    # ==================================================
    st.session_state["base_fund"] = fund_row
    return (
        f"📌 **Fund Details**\n\n"
        f"• Name: {fund_row['fund_name']}\n"
        f"• Type: {fund_row.get('fund_type', 'N/A')}\n"
        f"• NAV: {fund_row.get('nav', 'N/A')}\n\n"
        f"👉 Ask: **nav | returns | risk | compare with <fund>**"
    )
