import matplotlib.pyplot as plt
import streamlit as st


# ==========================================
# CLEAN SMALL RETURNS CHART
# ==========================================
def plot_returns_chart(fund_row, title="Returns"):

    periods = ["1Y", "3Y", "5Y"]

    returns = [
        fund_row.get("returns_1y", 0),
        fund_row.get("returns_3y", 0),
        fund_row.get("returns_5y", 0),
    ]

    clean_returns = []
    for r in returns:
        try:
            clean_returns.append(float(r))
        except:
            clean_returns.append(0)

    # Small & Clean figure
    fig, ax = plt.subplots(figsize=(4, 2.8))

    ax.bar(periods, clean_returns)

    ax.set_ylabel("Return %")
    ax.set_title("Returns Overview", fontsize=10)

    ax.tick_params(axis='x', labelsize=8)
    ax.tick_params(axis='y', labelsize=8)

    plt.tight_layout()

    st.pyplot(fig)


# ==========================================
# CLEAN SIDE-BY-SIDE COMPARISON CHART
# ==========================================
def plot_compare_returns(fund1, fund2):

    periods = ["1Y", "3Y", "5Y"]

    f1_returns = [
        fund1.get("returns_1y", 0),
        fund1.get("returns_3y", 0),
        fund1.get("returns_5y", 0),
    ]

    f2_returns = [
        fund2.get("returns_1y", 0),
        fund2.get("returns_3y", 0),
        fund2.get("returns_5y", 0),
    ]

    def clean(values):
        out = []
        for v in values:
            try:
                out.append(float(v))
            except:
                out.append(0)
        return out

    f1_clean = clean(f1_returns)
    f2_clean = clean(f2_returns)

    x = range(len(periods))

    fig, ax = plt.subplots(figsize=(5, 3))

    ax.bar([i - 0.2 for i in x], f1_clean, width=0.4, label="Fund 1")
    ax.bar([i + 0.2 for i in x], f2_clean, width=0.4, label="Fund 2")

    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=8)
    ax.set_ylabel("Return %", fontsize=8)
    ax.set_title("Return Comparison", fontsize=10)

    ax.legend(fontsize=7)

    plt.tight_layout()

    st.pyplot(fig)
