#!/usr/bin/env python3
"""GA4 API からデータを取得して input/ga4.csv を更新する"""

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
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )


def fetch(config):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest,
    )

    creds_path = os.path.join(BASE_DIR, config["CREDENTIALS_JSON"])
    client = BetaAnalyticsDataClient(credentials=_credentials(creds_path))

    days_back = int(config.get("DAYS_BACK", 28))
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back - 1)
    date_range = DateRange(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    property_id = config["GA4_PROPERTY_ID"]

    # ── メインクエリ ──────────────────────────────────────────────────────────
    main_resp = client.run_report(RunReportRequest(
        property=property_id,
        dimensions=[
            Dimension(name="hostName"),
            Dimension(name="pagePath"),
        ],
        metrics=[
            Metric(name="screenPageViews"),     # PV
            Metric(name="activeUsers"),          # アクティブユーザー
            Metric(name="userEngagementDuration"),  # エンゲージメント時間合計(秒)
            Metric(name="eventCount"),           # イベント数
            Metric(name="keyEvents"),            # キーイベント
        ],
        date_ranges=[date_range],
    ))

    # ── CTA クリッククエリ（eventName でフィルタ）──────────────────────────────
    cta_event = config.get("GA4_CTA_EVENT", "cta_click")
    cta_resp = client.run_report(RunReportRequest(
        property=property_id,
        dimensions=[
            Dimension(name="hostName"),
            Dimension(name="pagePath"),
        ],
        metrics=[Metric(name="eventCount")],
        date_ranges=[date_range],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value=cta_event),
            )
        ),
    ))

    # CTA データを (hostname, path) → count の dict に
    cta_map = {}
    for row in cta_resp.rows:
        key = (row.dimension_values[0].value, row.dimension_values[1].value)
        cta_map[key] = int(float(row.metric_values[0].value))

    # ── データ整形 ────────────────────────────────────────────────────────────
    rows = []
    for row in main_resp.rows:
        hostname = row.dimension_values[0].value
        path = row.dimension_values[1].value
        path = path if path.startswith("/") else f"/{path}"
        url = f"https://{hostname}{path}"

        pv = int(float(row.metric_values[0].value))
        active_users = int(float(row.metric_values[1].value))
        engagement_total = float(row.metric_values[2].value)
        avg_engagement_sec = round(engagement_total / pv, 1) if pv else 0.0
        event_count = int(float(row.metric_values[3].value))
        key_events = int(float(row.metric_values[4].value))
        cta_clicks = cta_map.get((hostname, path), 0)

        rows.append({
            "url": url,
            "pv": pv,
            "active_users": active_users,
            "avg_engagement_sec": avg_engagement_sec,
            "event_count": event_count,
            "key_events": key_events,
            "cta_clicks": cta_clicks,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        })

    out_path = os.path.join(BASE_DIR, "input", "ga4.csv")
    fieldnames = [
        "url", "pv", "active_users", "avg_engagement_sec",
        "event_count", "key_events", "cta_clicks",
        "period_start", "period_end",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"GA4: {len(rows)} 件 → {out_path}")
    return rows


if __name__ == "__main__":
    from _config import load_config
    fetch(load_config())
