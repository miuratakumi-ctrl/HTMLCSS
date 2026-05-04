#!/usr/bin/env python3
"""
Ahrefs API v3 からサイトの上位ページデータと参照ドメイン数を取得し
input/ahrefs_pages.csv に保存する。
"""

import csv
import os
import sys
import time
import requests
from datetime import date

_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from _config import load_config

AHREFS_API = "https://api.ahrefs.com/v3"
OUTPUT_FIELDS = [
    "url", "sum_traffic", "top_keyword", "top_keyword_best_position",
    "top_keyword_volume", "keywords", "referring_domains",
]


def _get(api_key, endpoint, params, retries=3):
    headers = {"Authorization": f"Bearer {api_key}"}
    params["output"] = "json"
    for attempt in range(retries):
        try:
            resp = requests.get(
                f"{AHREFS_API}/{endpoint}",
                params=params,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            if e.response.status_code == 429 and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise


def fetch_top_pages(api_key, target, limit=200):
    today = date.today()
    ref_date = date(today.year, today.month, 1).isoformat()
    data = _get(api_key, "site-explorer/top-pages", {
        "select": ",".join(OUTPUT_FIELDS),
        "target": target,
        "mode": "subdomains",
        "date": ref_date,
        "order_by": "sum_traffic:desc",
        "limit": limit,
    })
    return data.get("pages", [])


def fetch(config):
    api_key = config.get("AHREFS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("config.env に AHREFS_API_KEY が設定されていません")

    target = config.get("SITE_URL", "").strip()
    if not target:
        raise ValueError("config.env に SITE_URL が設定されていません")

    pages = fetch_top_pages(api_key, target)

    out_path = os.path.join(BASE_DIR, "input", "ahrefs_pages.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for page in pages:
            writer.writerow({k: page.get(k, "") for k in OUTPUT_FIELDS})

    print(f"Ahrefs: {len(pages)} ページ → input/ahrefs_pages.csv")


if __name__ == "__main__":
    from _config import load_config
    fetch(load_config())
