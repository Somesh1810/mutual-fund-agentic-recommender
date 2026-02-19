import os
import sys
import streamlit as st
import pandas as pd

# ---------------- PATH SETUP ----------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# ---------------- IMPORTS ----------------
from src.chat_ui import render_chat_ui
from src.data_fetch import fetch_live_nav
from src.preprocess import preprocess_hist_data, merge_hist_live
from src.recommender import agentic_recommender, detect_fund_type

# ---------------- STREAMLIT CONFIG ----------------
st.set_page_config(
    page_title="Mutual Fund Agentic Recommender",
    layout="wide"
)

st.title("📈 Mutual Fund Live Recommendation (Agentic AI + XAI)")

# ---------------- STREAMLIT CACHE ----------------
@st.cache_data(ttl=3600)
def get_live_nav():
    return fetch_live_nav()

# ---------------- SIDEBAR INPUTS ----------------
st.sidebar.header("User Preferences")

risk_appetite = st.sidebar.selectbox(
    "Risk Appetite", ["low", "medium", "high"]
)

horizon = st.sidebar.selectbox(
    "Investment Horizon", ["short", "medium", "long"]
)

invest_type = st.sidebar.selectbox(
    "Investment Type", ["sip", "lumpsum"]
)

amount = st.sidebar.number_input(
    "Amount", min_value=100.0, value=500.0, step=100.0
)

fund_type = st.sidebar.selectbox(
    "Fund Type",
    ["Equity", "Debt", "Gold", "Hybrid", "Other"]
)

top_n = st.sidebar.slider(
    "Top N Funds", 3, 10, 5
)

st.sidebar.markdown("---")

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.sidebar.file_uploader(
    "Upload Historical Dataset (CSV or AMFI TXT)",
    type=["csv", "txt"]
)

# ---------------- AMFI CACHE UPLOAD ----------------
CACHE_PATH = os.path.join(ROOT_DIR, "data", "amfi_nav_cache.txt")

st.sidebar.subheader("AMFI Cache File (Optional)")

cache_file = st.sidebar.file_uploader(
    "Upload amfi_nav_cache.txt",
    type=["txt"],
    key="cache_upload"
)

if cache_file is not None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "wb") as f:
        f.write(cache_file.getbuffer())
    st.sidebar.success("✅ Cache file saved")

# ---------------- MAIN FLOW ----------------
if uploaded_file is not None:

    # ---------- READ FILE ----------
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df_hist = pd.read_csv(uploaded_file)
        else:
            df_hist = pd.read_csv(
                uploaded_file,
                sep=";",
                engine="python",
                on_bad_lines="skip"
            )
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.stop()

    df_hist = preprocess_hist_data(df_hist)
    st.success("✅ Historical dataset uploaded")

    # ---------- RUN PIPELINE ----------
    if st.button("🚀 Run Live Recommendation"):

        with st.spinner("Fetching Live NAV from AMFI..."):
            try:
                df_live = get_live_nav()
                st.success("✅ Live NAV loaded")
            except Exception as e:
                st.error(f"❌ Failed to fetch NAV: {e}")
                st.stop()

        with st.spinner("Merging datasets..."):
            df_master = merge_hist_live(df_hist, df_live)

        # Ensure scheme_name exists
        if "scheme_name" not in df_master.columns:
            if "fund_name" in df_master.columns:
                df_master["scheme_name"] = df_master["fund_name"]
            else:
                st.error("❌ scheme_name column missing")
                st.stop()

        # Fund type classification
        df_master["fund_type"] = (
            df_master["scheme_name"]
            .apply(detect_fund_type)
            .astype(str)
            .str.title()
        )

        # ---------- DEBUG ----------
        st.subheader("🔍 Fund Type Distribution")
        st.write(df_master["fund_type"].value_counts())

        # ---------- RECOMMENDER ----------
        with st.spinner("Generating recommendations..."):
            top_funds, explanations = agentic_recommender(
                df_master=df_master,
                risk_appetite=risk_appetite,
                horizon=horizon,
                invest_type=invest_type,
                amount=amount,
                fund_type=fund_type,
                top_n=top_n
            )

        # ---------- OUTPUT ----------
        st.subheader("✅ Recommended Funds")

        if top_funds is not None and not top_funds.empty:

            # ✅ CLEAN & IMPORTANT METRICS ONLY
            display_cols = [
                "scheme_name",
                "fund_type",
                "nav",
                "returns_6m",
                "returns_1y",
                "returns_3y",
                "returns_5y",
                "returns_10y",
                "final_score"
            ]
            display_cols = [c for c in display_cols if c in top_funds.columns]

            st.dataframe(
                top_funds[display_cols].rename(columns={
                    "returns_6m": "6M Return (%)",
                    "returns_1y": "1Y Return (%)",
                    "returns_3y": "3Y Return (%)",
                    "returns_5y": "5Y Return (%)",
                    "returns_10y": "10Y Return (%)",
                    "final_score": "AI Score"
                }),
                use_container_width=True
            )

            import matplotlib.pyplot as plt

            st.subheader("📊 Performance Comparison (Top Funds)")

            if "returns_1y" in top_funds.columns:

                plot_data = top_funds.copy()

            # Clean numeric values safely
                plot_data["returns_1y"] = pd.to_numeric(
                    plot_data["returns_1y"], errors="coerce"
                )

                plot_data = plot_data.dropna(subset=["returns_1y"])

                if not plot_data.empty:

                    fig, ax = plt.subplots()

                    ax.bar(
                        plot_data["scheme_name"],
                        plot_data["returns_1y"]
                    )

                    ax.set_ylabel("1 Year Return (%)")
                    ax.set_title("Top Recommended Funds – 1Y Returns")
                    plt.xticks(rotation=45, ha="right")

                    st.pyplot(fig)

                else:
                    st.info("No valid return data available for chart.")


        else:
            st.warning("⚠️ No funds found for selected filters")

        # ---------- EXPLANATIONS ----------
        st.subheader("🧠 Agentic AI Explanation")
        if explanations:
            for exp in explanations:
                st.write(exp)
        else:
            st.info("No explanations generated")

else:
    st.info("⬅️ Upload historical data from sidebar to start")

# ---------------- FUND CHATBOT ----------------
st.markdown("---")
st.header("🤖 Fund Chat Assistant")

render_chat_ui()
