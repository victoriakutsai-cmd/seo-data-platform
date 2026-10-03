"""
Google Search Console API -> BigQuery (site totals + priority/brand keywords).

* One service account is added as a user to every GSC property.
* Site list comes from dim_site, so adding a site = adding one row.
* GSC data lags ~2-3 days, so each run re-pulls the last 5 days and replaces
  those partitions (late data gets picked up automatically).

Illustrative example written for this repository; not executed here.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROJECT, DATASET = "my-gcp-project", "seo_platform"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
LOOKBACK_DAYS = 5
ROW_LIMIT = 25_000


def gsc_client(key_path: str = "service_account.json"):
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def query_all(svc, prop: str, body: dict) -> list[dict]:
    """Paginate through searchanalytics.query (max 25k rows per call)."""
    rows, start = [], 0
    while True:
        resp = svc.searchanalytics().query(
            siteUrl=prop, body={**body, "rowLimit": ROW_LIMIT, "startRow": start}
        ).execute()
        batch = resp.get("rows", [])
        rows.extend(batch)
        if len(batch) < ROW_LIMIT:
            return rows
        start += ROW_LIMIT


def site_daily(svc, site_id: str, prop: str, d0: date, d1: date) -> pd.DataFrame:
    rows = query_all(svc, prop, {"startDate": str(d0), "endDate": str(d1),
                                 "dimensions": ["date"], "type": "web"})
    return pd.DataFrame([{
        "site_id": site_id, "data_date": r["keys"][0], "search_type": "web",
        "clicks": int(r["clicks"]), "impressions": int(r["impressions"]),
        # store like the bulk export: zero-based sum of positions
        "sum_position": (r["position"] - 1) * r["impressions"],
    } for r in rows])


def keyword_daily(svc, site_id: str, prop: str, keywords: dict[str, str],
                  d0: date, d1: date) -> pd.DataFrame:
    rows = query_all(svc, prop, {
        "startDate": str(d0), "endDate": str(d1), "dimensions": ["date", "query"], "type": "web",
        "dimensionFilterGroups": [{"groupType": "or", "filters": [
            {"dimension": "query", "operator": "equals", "expression": kw} for kw in keywords]}],
    })
    return pd.DataFrame([{
        "site_id": site_id, "data_date": r["keys"][0], "query": r["keys"][1],
        "keyword_group": keywords.get(r["keys"][1], "other"),
        "impressions": int(r["impressions"]), "clicks": int(r["clicks"]),
        "avg_position": round(r["position"], 1),
    } for r in rows])


def replace_window(bq: bigquery.Client, df: pd.DataFrame, table: str, d0: date, d1: date):
    """Delete the window, then append: idempotent re-pulls of late GSC data."""
    if df.empty:
        return
    fq = f"{PROJECT}.{DATASET}.{table}"
    bq.query(f"DELETE FROM `{fq}` WHERE data_date BETWEEN '{d0}' AND '{d1}' "
             f"AND site_id IN UNNEST(@ids)",
             job_config=bigquery.QueryJobConfig(query_parameters=[
                 bigquery.ArrayQueryParameter("ids", "STRING", df.site_id.unique().tolist())])
             ).result()
    df["data_date"] = pd.to_datetime(df["data_date"]).dt.date
    bq.load_table_from_dataframe(df, fq).result()


def main():
    bq = bigquery.Client(project=PROJECT)
    svc = gsc_client()
    d1 = date.today() - timedelta(days=2)
    d0 = d1 - timedelta(days=LOOKBACK_DAYS - 1)

    sites = bq.query(f"SELECT site_id, domain FROM `{PROJECT}.{DATASET}.dim_site`").to_dataframe()
    kw = bq.query(f"SELECT site_id, query, keyword_group FROM `{PROJECT}.{DATASET}.cfg_tracked_keywords`").to_dataframe()

    site_frames, kw_frames = [], []
    for s in sites.itertuples():
        prop = f"sc-domain:{s.domain}"
        site_frames.append(site_daily(svc, s.site_id, prop, d0, d1))
        kws = dict(kw[kw.site_id == s.site_id][["query", "keyword_group"]].values)
        if kws:
            kw_frames.append(keyword_daily(svc, s.site_id, prop, kws, d0, d1))

    replace_window(bq, pd.concat(site_frames), "raw_gsc_site_daily", d0, d1)
    if kw_frames:
        replace_window(bq, pd.concat(kw_frames), "raw_gsc_keyword_daily", d0, d1)
    print(f"GSC loaded {d0}..{d1} for {len(sites)} sites")


if __name__ == "__main__":
    main()
