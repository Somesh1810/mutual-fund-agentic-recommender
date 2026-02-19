import streamlit as st
import pandas as pd

from src.fund_qa import (
    load_fund_profiles,
    clean_query,
    find_best_match,
    select_best_scheme
)

# ================= CHATBOT LOGIC =================
def fund_chatbot_response(user_input: str) -> str:
    df = load_fund_profiles()

    if df is None or df.empty:
        return "⚠️ Fund data not loaded."

    # Session memory
    if "last_fund" not in st.session_state:
        st.session_state.last_fund = None

    q = user_input.lower().strip()
    cleaned = clean_query(user_input)
    result = find_best_match(df, cleaned)

    # -------- Intent detection --------
    is_nav = "nav" in q
    is_return = "return" in q
    is_risk = "risk" in q
    is_details = "detail" in q or "about" in q

    has_intent = is_nav or is_return or is_risk or is_details

    fund = None  # 🔑 ALWAYS initialize

    # -------- Multiple matches --------
    if isinstance(result, pd.DataFrame):
        if has_intent:
            fund = select_best_scheme(result)
            st.session_state.last_fund = fund
        else:
            # AMC-level listing
            names = (
                result["fund_name"]
                .str.replace(r" - Direct.*", "", regex=True)
                .str.replace(r" - Regular.*", "", regex=True)
                .unique()[:6]
            )

            fund_list = "\n".join(f"• {n}" for n in names)

            return (
                "🏦 **Funds under this AMC:**\n\n"
                f"{fund_list}\n\n"
                "👉 Ask about a specific fund for NAV, returns, or risk."
            )

    # -------- Single match --------
    elif isinstance(result, pd.Series):
        fund = result
        st.session_state.last_fund = fund

    # -------- Memory fallback --------
    else:
        fund = st.session_state.last_fund

    # -------- No fund found --------
    if fund is None:
        return (
            "❌ I couldn't find that fund.\n\n"
            "Try typing:\n"
            "• hdfc flexi cap\n"
            "• nippon india large cap\n"
            "• sbi bluechip"
        )

    name = fund.get("fund_name", "Unknown Fund")

    # -------- NAV --------
    if is_nav:
        return f"💰 NAV of **{name}** is **{fund.get('nav', 'N/A')}**"

    # -------- RETURNS --------
    if is_return:
        return (
            f"📈 **Returns – {name}**\n\n"
            f"• 1Y: {fund.get('returns_1y', 'N/A')}\n"
            f"• 3Y: {fund.get('returns_3y', 'N/A')}\n"
            f"• 5Y: {fund.get('returns_5y', 'N/A')}"
        )

    # -------- RISK --------
    if is_risk:
        ftype = str(fund.get("fund_type", "")).lower()
        if "equity" in ftype:
            risk = "Moderate to High risk"
        elif "debt" in ftype:
            risk = "Low to Moderate risk"
        else:
            risk = "Moderate risk"

        return f"⚠️ **{name}** is considered **{risk}**"

    # -------- DETAILS / DEFAULT --------
    return (
        f"📊 **Fund Details**\n\n"
        f"📌 Name: {name}\n"
        f"📂 Type: {fund.get('fund_type', 'N/A')}\n"
        f"💰 NAV: {fund.get('nav', 'N/A')}\n\n"
        f"👉 Ask: nav | returns | risk"
    )


# ================= CHAT UI =================
def render_chat_ui():
    st.subheader("💬 Fund Chat Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ✅ SINGLE chat_input (no duplicates)
    user_input = st.chat_input(
        "Ask about a fund (e.g. 'nav of hdfc flexi cap')",
        key="fund_chat_input"
    )

    if user_input:
        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        response = fund_chatbot_response(user_input)

        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )

        with st.chat_message("assistant"):
            st.markdown(response)
