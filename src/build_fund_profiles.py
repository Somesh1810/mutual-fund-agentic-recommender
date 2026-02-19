import os
import pandas as pd

from src.preprocess import preprocess_hist_data, merge_hist_live
from src.data_fetch import fetch_live_nav
from src.recommender import detect_fund_type


def load_navall_txt(txt_path: str) -> pd.DataFrame:
    df = pd.read_csv(
        txt_path,
        sep=";",
        engine="python",
        on_bad_lines="skip"
    )

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    if "scheme_code" not in df.columns:
        raise Exception(f"❌ scheme_code not found. Columns: {df.columns.tolist()}")

    return df


def build_fund_profiles(hist_txt_path: str, output_path: str = "data/fund_profiles.csv"):

    # 1) Load historical NAVAll.txt
    df_hist = load_navall_txt(hist_txt_path)
    df_hist = preprocess_hist_data(df_hist)

    # 2) Fetch live NAV
    df_live = fetch_live_nav()

    # 3) Merge
    df_master = merge_hist_live(df_hist, df_live)

    # 4) Pick fund name column
    name_col = "scheme_name" if "scheme_name" in df_master.columns else "fund_name"

    # 5) Fund type
    df_master["fund_type"] = df_master[name_col].apply(detect_fund_type)

    # 6) Keep latest record per scheme_code
    if "date" in df_master.columns:
        df_master["date"] = pd.to_datetime(df_master["date"], errors="coerce")
        df_master = df_master.dropna(subset=["date"])
        df_master = df_master.sort_values("date")
        df_profiles = df_master.groupby("scheme_code").tail(1).copy()
    else:
        df_profiles = df_master.copy()

    # 7) Save without returns (FAST)
    final_cols = ["scheme_code", name_col, "fund_type", "nav", "date", "nav_change_pct"]
    final_cols = [c for c in final_cols if c in df_profiles.columns]
    df_profiles = df_profiles[final_cols].copy()

    df_profiles = df_profiles.rename(columns={name_col: "fund_name"})

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_profiles.to_csv(output_path, index=False)

    print(f"✅ fund_profiles.csv created successfully at: {output_path}")
    print("✅ Total funds:", df_profiles.shape[0])

    return df_profiles


if __name__ == "__main__":
    build_fund_profiles("data/NAVAll.txt")
