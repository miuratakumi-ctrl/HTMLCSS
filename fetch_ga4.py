#!/usr/bin/env python3
import csv, os, sys
from datetime import date, timedelta
_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)
if _SRC not in sys.path: sys.path.insert(0, _SRC)

def _creds(path):
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(
        path, scopes=["https://www.googleapis.com/auth/analytics.readonly"])

def fetch(config, target_date=None, start_date=None, end_date=None, out_path=None):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest)
    creds_path = os.path.join(BASE_DIR, config["CREDENTIALS_JSON"])
    client = BetaAnalyticsDataClient(credentials=_creds(creds_path))

    # 日付範囲の決定（優先順: start/end > target_date > DAYS_BACK）
    if start_date and end_date:
        pass
    elif target_date:
        start_date = end_date = target_date
    else:
        days = int(config.get("DAYS_BACK", 28))
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)

    dr = DateRange(start_date=start_date.isoformat(), end_date=end_date.isoformat())
    pid = config["GA4_PROPERTY_ID"]

    main_resp = client.run_report(RunReportRequest(
        property=pid,
        dimensions=[Dimension(name="hostName"), Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers"),
                 Metric(name="userEngagementDuration"), Metric(name="eventCount"),
                 Metric(name="keyEvents")],
        date_ranges=[dr]))

    # ↓ デフォルトを "click" に変更（config.env で GA4_CTA_EVENT=xxx と書けば上書き可）
    cta_event = config.get("GA4_CTA_EVENT", "click")
    cta_resp = client.run_report(RunReportRequest(
        property=pid,
        dimensions=[Dimension(name="hostName"), Dimension(name="pagePath")],
        metrics=[Metric(name="eventCount")],
        date_ranges=[dr],
        dimension_filter=FilterExpression(filter=Filter(
            field_name="eventName",
            string_filter=Filter.StringFilter(value=cta_event)))))
    cta_map = {(r.dimension_values[0].value, r.dimension_values[1].value):
               int(float(r.metric_values[0].value)) for r in cta_resp.rows}

    rows = []
    for row in main_resp.rows:
        hn = row.dimension_values[0].value
        path = row.dimension_values[1].value
        if not path.startswith("/"): path = "/" + path
        url = f"https://{hn}{path}"
        pv = int(float(row.metric_values[0].value))
        eng = float(row.metric_values[2].value)
        rows.append({"url": url, "pv": pv,
            "active_users": int(float(row.metric_values[1].value)),
            "avg_engagement_sec": round(eng / pv, 1) if pv else 0.0,
            "event_count": int(float(row.metric_values[3].value)),
            "key_events": int(float(row.metric_values[4].value)),
            "cta_clicks": cta_map.get((hn, path), 0),
            "period_start": start_date.isoformat(), "period_end": end_date.isoformat()})

    out = out_path or os.path.join(BASE_DIR, "input", "ga4.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader(); w.writerows(rows)
    print(f"GA4: {len(rows)} 件（{start_date}〜{end_date}）→ {out}")

if __name__ == "__main__":
    from _config import load_config
    fetch(load_config())
