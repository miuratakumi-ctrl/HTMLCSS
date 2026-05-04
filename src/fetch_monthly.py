#!/usr/bin/env python3
"""
月次データ取得:
  GA4 / GSC の当月累計・前月全期間データを取得し、
  input/ga4_current_month.csv
  input/ga4_prev_month.csv
  input/gsc_current_month.csv
  input/gsc_prev_month.csv
  に保存する。

引数:
  target_date (date | None): 集計の基準日。
    指定した場合 → その日を当月末とみなして当月/前月を算出
    None の場合  → 昨日を基準に算出
"""

import calendar
import csv
import os
import sys
from datetime import date, timedelta

_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Filter, FilterExpression, Metric,
    MetricAggregation, RunReportRequest,
)
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ── 認証 ─────────────────────────────────────────────────────────────────────

def _creds(config):
    key_path = os.path.join(BASE_DIR, config["CREDENTIALS_JSON"])
    scopes = [
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]
    return service_account.Credentials.from_service_account_file(
        key_path, scopes=scopes
    )


# ── GA4 クエリ ────────────────────────────────────────────────────────────────

def _query_ga4(client, property_id, start_date, end_date):
    pid = (property_id if property_id.startswith("properties/")
           else f"properties/{property_id}")
    req = RunReportRequest(
        property=pid,
        dimensions=[Dimension(name="hostName"), Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="activeUsers"),
            Metric(name="userEngagementDuration"),
            Metric(name="eventCount"),
            Metric(name="keyEvents"),
        ],
        date_ranges=[DateRange(
            start_date=str(start_date), end_date=str(end_date)
        )],
        metric_aggregations=[MetricAggregation.TOTAL],
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        host = row.dimension_values[0].value
        path = row.dimension_values[1].value
        users = max(int(row.metric_values[1].value), 1)
        rows.append({
            "article_url": f"https://{host}{path}",
            "pv": int(row.metric_values[0].value),
            "active_users": int(row.metric_values[1].value),
            "avg_engagement_sec": round(
                float(row.metric_values[2].value) / users, 1
            ),
            "event_count": int(row.metric_values[3].value),
            "key_events": int(row.metric_values[4].value),
        })
    return rows


def _query_ga4_cta(client, property_id, start_date, end_date, event_name):
    pid = (property_id if property_id.startswith("properties/")
           else f"properties/{property_id}")
    req = RunReportRequest(
        property=pid,
        dimensions=[Dimension(name="hostName"), Dimension(name="pagePath")],
        metrics=[Metric(name="eventCount")],
        date_ranges=[DateRange(
            start_date=str(start_date), end_date=str(end_date)
        )],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value=event_name),
            )
        ),
    )
    resp = client.run_report(req)
    result = {}
    for row in resp.rows:
        host = row.dimension_values[0].value
        path = row.dimension_values[1].value
        result[f"https://{host}{path}"] = int(row.metric_values[0].value)
    return result


# ── GSC クエリ ────────────────────────────────────────────────────────────────

def _query_gsc(service, site, start_date, end_date):
    rows_all = []
    start_row = 0
    while True:
        body = {
            "startDate": str(start_date),
            "endDate": str(end_date),
            "dimensions": ["page"],
            "rowLimit": 25000,
            "startRow": start_row,
        }
        res = service.searchanalytics().query(
            siteUrl=site, body=body
        ).execute()
        rows = res.get("rows", [])
        if not rows:
            break
        rows_all.extend(rows)
        if len(rows) < 25000:
            break
        start_row += len(rows)
    return rows_all


# ── CSV 書き出し ──────────────────────────────────────────────────────────────

_GA4_FIELDS = [
    "article_url", "pv", "active_users", "avg_engagement_sec",
    "event_count", "key_events", "cta_clicks",
]
_GSC_FIELDS = ["article_url", "impressions", "clicks", "ctr_%", "position"]


def _write_ga4(path, rows, cta_map):
    for r in rows:
        r["cta_clicks"] = cta_map.get(r["article_url"], 0)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_GA4_FIELDS)
        w.writeheader()
        w.writerows(rows)


def _write_gsc(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_GSC_FIELDS)
        w.writeheader()
        for row in rows:
            clicks = row.get("clicks", 0)
            impr   = row.get("impressions", 0)
            w.writerow({
                "article_url": row["keys"][0],
                "impressions": impr,
                "clicks": clicks,
                "ctr_%": round(clicks / impr * 100, 2) if impr > 0 else 0,
                "position": round(row.get("position", 0), 1),
            })


# ── メイン ────────────────────────────────────────────────────────────────────

def fetch(config, target_date=None):
    # 基準日: target_date が指定されていれば使用、なければ昨日
    if target_date is None:
        reference = date.today() - timedelta(days=1)
    else:
        reference = (target_date
                     if isinstance(target_date, date)
                     else date.fromisoformat(str(target_date)))

    # 当月: 基準日の月の 1 日 → 基準日
    cur_start = date(reference.year, reference.month, 1)
    cur_end   = reference

    # 前月: 基準日の前カレンダー月の全期間
    if reference.month == 1:
        prev_year, prev_month = reference.year - 1, 12
    else:
        prev_year, prev_month = reference.year, reference.month - 1
    prev_start = date(prev_year, prev_month, 1)
    prev_end   = date(
        prev_year, prev_month,
        calendar.monthrange(prev_year, prev_month)[1]
    )

    creds      = _creds(config)
    ga4_client = BetaAnalyticsDataClient(credentials=creds)
    gsc_svc    = build("searchconsole", "v1", credentials=creds,
                       cache_discovery=False)

    pid       = config["GA4_PROPERTY_ID"]
    site      = config["GSC_PROPERTY"]
    cta_event = config.get("GA4_CTA_EVENT", "cta_click")
    input_dir = os.path.join(BASE_DIR, "input")

    # GA4 当月
    cur_rows = _query_ga4(ga4_client, pid, cur_start, cur_end)
    cur_cta  = _query_ga4_cta(ga4_client, pid, cur_start, cur_end, cta_event)
    _write_ga4(os.path.join(input_dir, "ga4_current_month.csv"),
               cur_rows, cur_cta)
    print(f"GA4 当月: {len(cur_rows)} 件（{cur_start}〜{cur_end}）"
          f" → input/ga4_current_month.csv")

    # GA4 前月
    prev_rows = _query_ga4(ga4_client, pid, prev_start, prev_end)
    prev_cta  = _query_ga4_cta(ga4_client, pid, prev_start, prev_end, cta_event)
    _write_ga4(os.path.join(input_dir, "ga4_prev_month.csv"),
               prev_rows, prev_cta)
    print(f"GA4 前月: {len(prev_rows)} 件（{prev_start}〜{prev_end}）"
          f" → input/ga4_prev_month.csv")

    # GSC 当月
    gsc_cur = _query_gsc(gsc_svc, site, cur_start, cur_end)
    _write_gsc(os.path.join(input_dir, "gsc_current_month.csv"), gsc_cur)
    print(f"GSC 当月: {len(gsc_cur)} 件（{cur_start}〜{cur_end}）"
          f" → input/gsc_current_month.csv")

    # GSC 前月
    gsc_prev = _query_gsc(gsc_svc, site, prev_start, prev_end)
    _write_gsc(os.path.join(input_dir, "gsc_prev_month.csv"), gsc_prev)
    print(f"GSC 前月: {len(gsc_prev)} 件（{prev_start}〜{prev_end}）"
          f" → input/gsc_prev_month.csv")


if __name__ == "__main__":
    from _config import load_config
    fetch(load_config())
