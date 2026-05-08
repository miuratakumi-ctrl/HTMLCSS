#!/usr/bin/env python3
import csv, os, sys
from datetime import date, timedelta
_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)
if _SRC not in sys.path: sys.path.insert(0, _SRC)

def _creds(path):
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(
        path, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])

def fetch(config, target_date=None, start_date=None, end_date=None, out_path=None):
    from googleapiclient.discovery import build
    creds_path = os.path.join(BASE_DIR, config["CREDENTIALS_JSON"])
    svc = build("searchconsole", "v1", credentials=_creds(creds_path), cache_discovery=False)

    # 日付範囲の決定（優先順: start/end > target_date > DAYS_BACK）
    if start_date and end_date:
        start, end = start_date, end_date
    elif target_date:
        start = end = target_date
    else:
        days = int(config.get("DAYS_BACK", 28))
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=days - 1)

    prop = config["GSC_PROPERTY"]
    rows, start_row, limit = [], 0, 25000
    while True:
        resp = svc.searchanalytics().query(siteUrl=prop, body={
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": ["page"], "rowLimit": limit, "startRow": start_row
        }).execute()
        batch = resp.get("rows", [])
        if not batch: break
        for r in batch:
            rows.append({"url": r["keys"][0],
                "impressions": int(r.get("impressions", 0)),
                "clicks": int(r.get("clicks", 0)),
                "ctr": round(float(r.get("ctr", 0)) * 100, 2),
                "position": round(float(r.get("position", 0)), 1),
                "period_start": start.isoformat(), "period_end": end.isoformat()})
        if len(batch) < limit: break
        start_row += limit

    out = out_path or os.path.join(BASE_DIR, "input", "gsc.csv")
    fieldnames = ["url", "impressions", "clicks", "ctr", "position", "period_start", "period_end"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)
    print(f"GSC: {len(rows)} 件（{start}〜{end}）→ {out}")

if __name__ == "__main__":
    from _config import load_config
    fetch(load_config())
