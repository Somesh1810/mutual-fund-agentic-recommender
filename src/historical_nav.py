import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta


def fetch_scheme_history(scheme_code: str) -> pd.DataFrame:
    """
    Fetch NAV history of a single scheme from AMFI endpoint.
    """
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()

    data = r.json()

    if "data" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    df = df.dropna(subset=["date", "nav"]).sort_values("date")
    return df


def calc_return(df_nav, years=None, months=None):
    """
    Calculate return from nearest date in past.
    """
    if df_nav.empty:
        return None

    latest = df_nav.iloc[-1]
    latest_nav = latest["nav"]
    latest_date = latest["date"]

    if years:
        target_date = latest_date - timedelta(days=365 * years)
    elif months:
        target_date = latest_date - timedelta(days=30 * months)
    else:
        return None

    # Find closest past NAV
    past_df = df_nav[df_nav["date"] <= target_date]
    if past_df.empty:
        return None

    past_nav = past_df.iloc[-1]["nav"]

    return ((latest_nav - past_nav) / past_nav) * 100


def compute_all_returns(scheme_code: str) -> dict:
    """
    Returns dict: 6m,1y,2y,3y,5y,10y
    """
    df_nav = fetch_scheme_history(scheme_code)

    return {
        "returns_6m": calc_return(df_nav, months=6),
        "returns_1y": calc_return(df_nav, years=1),
        "returns_2y": calc_return(df_nav, years=2),
        "returns_3y": calc_return(df_nav, years=3),
        "returns_5y": calc_return(df_nav, years=5),
        "returns_10y": calc_return(df_nav, years=10),
    }
