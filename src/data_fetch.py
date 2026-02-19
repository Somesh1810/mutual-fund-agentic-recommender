import os
import time
import requests
import pandas as pd
from io import StringIO

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "amfi_nav_cache.txt")


def fetch_amfi_text(retries=3):
    headers = {"User-Agent": "Mozilla/5.0"}

    for _ in range(retries):
        try:
            r = requests.get(AMFI_URL, headers=headers, timeout=20)
            r.raise_for_status()

            if "<html" in r.text.lower():
                raise Exception("AMFI returned HTML error page")

            return r.text
        except Exception:
            time.sleep(3)

    raise Exception("AMFI not responding after retries")


def save_cache(text: str):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        f.write(text)


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return None


def parse_amfi_text(text: str):
    # keep only real data rows
    valid_lines = [line for line in text.splitlines() if ";" in line]

    df = pd.read_csv(StringIO("\n".join(valid_lines)), sep=";", header=0)

    df = df.rename(columns={
        "Scheme Code": "scheme_code",
        "Scheme Name": "fund_name",
        "Net Asset Value": "nav",
        "Date": "date"
    })

    df["scheme_code"] = df["scheme_code"].astype(str)
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    df = df.dropna(subset=["scheme_code", "nav"])

    return df[["scheme_code", "fund_name", "nav", "date"]]


def fetch_live_nav():
    """
    Fetch NAV from AMFI. If AMFI fails, use cached file.
    """
    try:
        text = fetch_amfi_text()
        save_cache(text)
        df = parse_amfi_text(text)
        df.attrs["source"] = "LIVE AMFI"
        return df

    except Exception:
        text = load_cache()
        if text is None:
            raise Exception("AMFI failed and cache file not found. Upload NAVAll.txt once.")

        df = parse_amfi_text(text)
        df.attrs["source"] = "LOCAL CACHE"
        return df
