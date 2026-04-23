#!/usr/bin/env python3
"""GSC API からデータを取得して input/gsc.csv を更新する"""

import csv
import os
import sys
from datetime import date, timedelta

_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _credentials(creds_path):
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )


def fetch(config):
    from googleapiclient.discovery import build

    creds_path = os.path.join(BASE_DIR, config["CREDENTIALS_JSON"])
    service = build(
        "searchconsole", "v1",
        credentials=_credentials(creds_path),
        cache_discovery=False,
    )

    days_back = int(config.get("DAYS_BACK", 28))
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back - 1)

    gsc_property = config["GSC_PROPERTY"]
    rows = []
    start_row = 0
    row_limit = 25000  # GSC の最大行数

    while True:
        response = (
            service.searchanalytics()
            .query(
                siteUrl=gsc_property,
                body={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "dimensions": ["page"],
                    "rowLimit": row_limit,
                    "startRow": start_row,
                },
            )
            .execute()
        )

        batch = response.get("rows", [])
        if not batch:
            break

        for row in batch:
            rows.append({
                "url": row["keys"][0],
                "impressions": int(row.get("impressions", 0)),
                "clicks": int(row.get("clicks", 0)),
                "ctr": round(float(row.get("ctr", 0)) * 100, 2),  # % 表示
                "position": round(float(row.get("position", 0)), 1),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
            })

        if len(batch) < row_limit:
            break
        start_row += row_limit

    out_path = os.path.join(BASE_DIR, "input", "gsc.csv")
    fieldnames = ["url", "impressions", "clicks", "ctr", "position",
                  "period_start", "period_end"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"GSC: {len(rows)} 件 → {out_path}")
    return rows


if __name__ == "__main__":
    from _config import load_config
    fetch(load_config())
