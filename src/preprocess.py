import pandas as pd


def preprocess_hist_data(df_hist: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names for any uploaded dataset (CSV or TXT parsed).
    """
    df_hist = df_hist.copy()
    df_hist.columns = (
        df_hist.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df_hist


def _ensure_column(df: pd.DataFrame, target: str, possible_names: list) -> pd.DataFrame:
    """
    If target column doesn't exist, try renaming from possible_names.
    """
    df = df.copy()

    if target in df.columns:
        return df

    for col in possible_names:
        if col in df.columns:
            df = df.rename(columns={col: target})
            return df

    # Try fuzzy match (contains)
    for col in df.columns:
        if all(x in col for x in target.split("_")):
            df = df.rename(columns={col: target})
            return df

    return df


def merge_hist_live(df_hist: pd.DataFrame, df_live: pd.DataFrame) -> pd.DataFrame:
    """
    Merge historical NAV dataset with live AMFI NAV dataset using scheme_code.
    Works for:
    - historical.csv
    - NAVAll.txt parsed into DataFrame
    """

    df_hist = preprocess_hist_data(df_hist)
    df_live = preprocess_hist_data(df_live)

    # --- Ensure scheme_code exists in both ---
    df_hist = _ensure_column(df_hist, "scheme_code", ["scheme_code", "scheme_code_"])
    df_live = _ensure_column(df_live, "scheme_code", ["scheme_code", "scheme_code_"])

    if "scheme_code" not in df_hist.columns:
        raise Exception(f"❌ scheme_code missing in historical file. Columns: {df_hist.columns.tolist()}")

    if "scheme_code" not in df_live.columns:
        raise Exception(f"❌ scheme_code missing in live NAV file. Columns: {df_live.columns.tolist()}")

    # --- Ensure scheme_name exists in hist ---
    df_hist = _ensure_column(df_hist, "scheme_name", ["scheme_name", "scheme"])
    # --- Ensure scheme_name exists in live ---
    df_live = _ensure_column(df_live, "scheme_name", ["scheme_name", "scheme"])

    # --- Ensure net_asset_value exists in hist ---
    df_hist = _ensure_column(df_hist, "net_asset_value", ["net_asset_value", "nav", "netassetvalue"])
    # --- Ensure date exists in hist ---
    df_hist = _ensure_column(df_hist, "date", ["date", "nav_date"])

    # Convert scheme_code type
    df_hist["scheme_code"] = df_hist["scheme_code"].astype(str).str.strip()
    df_live["scheme_code"] = df_live["scheme_code"].astype(str).str.strip()

    # Merge
    df_master = pd.merge(df_hist, df_live, on="scheme_code", how="inner", suffixes=("_hist", "_live"))

    # Fix scheme_name column after merge
    if "scheme_name" not in df_master.columns:
        if "scheme_name_hist" in df_master.columns:
            df_master = df_master.rename(columns={"scheme_name_hist": "scheme_name"})
        elif "scheme_name_live" in df_master.columns:
            df_master = df_master.rename(columns={"scheme_name_live": "scheme_name"})

    # Convert numeric columns
    if "net_asset_value" in df_master.columns:
        df_master["net_asset_value"] = pd.to_numeric(df_master["net_asset_value"], errors="coerce")

    if "nav" in df_master.columns:
        df_master["nav"] = pd.to_numeric(df_master["nav"], errors="coerce")

    # Convert date
    if "date" in df_master.columns:
        df_master["date"] = pd.to_datetime(df_master["date"], errors="coerce")

    # NAV change calculations
    if "net_asset_value" in df_master.columns and "nav" in df_master.columns:
        df_master["nav_change"] = df_master["nav"] - df_master["net_asset_value"]
        df_master["nav_change_pct"] = (df_master["nav_change"] / df_master["net_asset_value"]) * 100
    else:
        df_master["nav_change"] = None
        df_master["nav_change_pct"] = None

    return df_master
