"""
GA4 Data API + PageSpeed Insights API -> BigQuery.

* GA4: sessions / engaged sessions / sign_up events by default channel group.
* PSI: weekly Core Web Vitals per site (mobile + desktop). LCP and CLS come from
  the lab run; INP only exists in field (CrUX) data, so it is read from
  loadingExperience when the site has enough traffic.

Illustrative example written for this repository; not executed here.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import requests
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (DateRange, Dimension, Filter,
                                                FilterExpression, Metric,
                                                RunReportRequest)
from google.cloud import bigquery

PROJECT, DATASET = "my-gcp-project", "seo_platform"
PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


# ------------------------------- GA4 --------------------------------------- #
def ga4_channel_daily(client: BetaAnalyticsDataClient, site_id: str, property_id: str,
                      d0: date, d1: date) -> pd.DataFrame:
    def run(metrics, dim_filter=None):
        req = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="date"), Dimension(name="sessionDefaultChannelGroup")],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=str(d0), end_date=str(d1))],
            dimension_filter=dim_filter, limit=100_000)
        rows = client.run_report(req).rows
        return {(r.dimension_values[0].value, r.dimension_values[1].value):
                [float(v.value) for v in r.metric_values] for r in rows}

    sessions = run(["sessions", "engagedSessions"])
    signups = run(["eventCount"], FilterExpression(filter=Filter(
        field_name="eventName", string_filter=Filter.StringFilter(value="sign_up"))))
    return pd.DataFrame([{
        "site_id": site_id, "date": pd.to_datetime(k[0]).date(),
        "session_default_channel_group": k[1],
        "sessions": int(v[0]), "engaged_sessions": int(v[1]),
        "sign_up_events": int(signups.get(k, [0])[0]),
    } for k, v in sessions.items()])


# ------------------------------- PSI --------------------------------------- #
def psi_check(site_id: str, url: str, strategy: str) -> dict:
    r = requests.get(PSI_URL, params={"url": url, "strategy": strategy,
                                      "category": "performance",
                                      "key": os.environ["PSI_API_KEY"]}, timeout=120)
    r.raise_for_status()
    j = r.json()
    audits = j["lighthouseResult"]["audits"]
    field = j.get("loadingExperience", {}).get("metrics", {})
    return {
        "site_id": site_id, "check_date": date.today(), "strategy": strategy,
        "lcp_ms": audits["largest-contentful-paint"]["numericValue"],
        "inp_ms": field.get("INTERACTION_TO_NEXT_PAINT", {}).get("percentile"),
        "cls": audits["cumulative-layout-shift"]["numericValue"],
        "performance_score": j["lighthouseResult"]["categories"]["performance"]["score"] * 100,
    }


def main():
    bq = bigquery.Client(project=PROJECT)
    sites = bq.query(f"SELECT site_id, domain, ga4_property_id FROM `{PROJECT}.{DATASET}.dim_site`").to_dataframe()

    # GA4: re-pull last 3 days (GA4 finalises data within ~48h)
    d1 = date.today() - timedelta(days=1)
    d0 = d1 - timedelta(days=2)
    ga = BetaAnalyticsDataClient()
    ga_df = pd.concat([ga4_channel_daily(ga, s.site_id, s.ga4_property_id, d0, d1)
                       for s in sites.itertuples()])
    bq.query(f"DELETE FROM `{PROJECT}.{DATASET}.raw_ga4_channel_daily` "
             f"WHERE date BETWEEN '{d0}' AND '{d1}'").result()
    bq.load_table_from_dataframe(ga_df, f"{PROJECT}.{DATASET}.raw_ga4_channel_daily").result()

    # PSI: weekly (Mondays)
    if date.today().weekday() == 0:
        psi = [psi_check(s.site_id, f"https://{s.domain}/", st)
               for s in sites.itertuples() for st in ("mobile", "desktop")]
        bq.load_table_from_dataframe(pd.DataFrame(psi), f"{PROJECT}.{DATASET}.raw_psi_cwv_weekly").result()


if __name__ == "__main__":
    main()
