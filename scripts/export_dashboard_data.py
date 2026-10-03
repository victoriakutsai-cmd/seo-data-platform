"""
Export a compact JSON snapshot of the marts for the static dashboard.

    python scripts/run_local.py
    python scripts/export_dashboard_data.py     # -> dashboard_data.json
    python scripts/build_dashboard.py           # -> docs/index.html
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_local  # noqa: E402  (registers the BigQuery-function UDFs used by staging views)

con = run_local.connect()
q = lambda s: pd.read_sql(s, con)

sites = q("SELECT site_id, brand, vertical, geo, market, avg_cpc_eur FROM dim_site ORDER BY site_id")
si = {s: i for i, s in enumerate(sites.site_id)}
months = sorted(q("SELECT DISTINCT month FROM mart_site_monthly").month)
mi = {m: i for i, m in enumerate(months)}
CH = ["organic", "direct", "paid", "referral", "social"]
prev_m = months[-2][:7]

# monthly per site x channel: clicks, signups, new customers, net revenue
d = q("""SELECT site_id, substr(date,1,7)||'-01' AS month, channel, SUM(clicks) c, SUM(signups) s,
         SUM(new_customers) n, ROUND(SUM(net_revenue_eur)) r FROM mart_site_daily GROUP BY 1,2,3""")
rows = [[si[r.site_id], mi[r.month], CH.index(r.channel), int(r.c), int(r.s), int(r.n), int(r.r)] for r in d.itertuples()]

# daily per site x channel for the previous and current month (MTD views)
dd = q(f"""SELECT site_id, date, channel, clicks c, signups s, new_customers n, ROUND(net_revenue_eur) r
          FROM mart_site_daily WHERE date >= '{prev_m}-01'""")
daily = [[si[r.site_id], 0 if r.date.startswith(prev_m) else 1, int(r.date[8:10]), CH.index(r.channel),
          int(r.c), int(r.s), int(r.n), int(r.r)] for r in dd.itertuples()]

# targets per site x month x channel
t = q("SELECT site_id, month, channel, new_customers_target n, net_revenue_target_eur r FROM raw_targets_monthly")
targets = [[si[r.site_id], mi[r.month], CH.index(r.channel), int(r.n), int(r.r)] for r in t.itertuples() if r.month in mi]

# Search Console brand / non-brand: monthly and daily
g = q("""SELECT site_id, month, gsc_brand_clicks b, gsc_nonbrand_clicks nb,
         gsc_brand_impressions bi, gsc_nonbrand_impressions nbi FROM mart_site_monthly""")
gsc = [[si[r.site_id], mi[r.month], int(r.b or 0), int(r.nb or 0), int(r.bi or 0), int(r.nbi or 0)] for r in g.itertuples()]
gd = q(f"SELECT site_id, date, brand_clicks b, nonbrand_clicks nb FROM stg_gsc_site_daily WHERE date >= '{prev_m}-01'")
gsc_daily = [[si[r.site_id], 0 if r.date.startswith(prev_m) else 1, int(r.date[8:10]), int(r.b), int(r.nb)] for r in gd.itertuples()]

# keyword position distribution (non-brand keywords) per site x month
k = q("""SELECT site_id, month, SUM(pos_1_3) a, SUM(pos_4_10) b, SUM(pos_11_20) c, SUM(pos_21_100) d, SUM(not_ranking) e
         FROM mart_keyword_positions WHERE keyword_group != 'brand' GROUP BY 1, 2""")
kw = [[si[r.site_id], mi[r.month], int(r.a), int(r.b), int(r.c), int(r.d), int(r.e)] for r in k.itertuples() if r.month in mi]

# technical health: latest week and 4 weeks earlier
h = q("SELECT * FROM mart_technical_health")
last = h.check_date.max()
prev4 = sorted(h.check_date.unique())[-5]
hl, hp = h[h.check_date == last].set_index("site_id"), h[h.check_date == prev4].set_index("site_id")
health = [[si[s], round(hl.loc[s].tech_health_score, 1), round(hp.loc[s].tech_health_score, 1),
           int(hl.loc[s].lcp_ms), int(hl.loc[s].inp_ms), round(hl.loc[s].cls, 2), int(hl.loc[s].cwv_pass),
           round(hl.loc[s].indexation_rate, 3), int(hl.loc[s].errors_4xx), int(hl.loc[s].errors_5xx),
           int(hl.loc[s].broken_internal_links), round(hl.loc[s].uptime_pct, 2)] for s in sites.site_id]

p = q("SELECT report_date, days_elapsed, days_in_month FROM mart_target_pacing LIMIT 1").iloc[0]
mt = q("SELECT gsc_data_until FROM mart_mtd_comparison LIMIT 1").iloc[0]

out = {
    "sites": sites.values.tolist(), "months": months, "channels": CH,
    "rows": rows, "daily": daily, "targets": targets, "gsc": gsc, "gscDaily": gsc_daily, "kw": kw,
    "health": health, "healthDates": [last, prev4],
    "cal": {"report_date": p.report_date, "days_elapsed": int(p.days_elapsed), "days_in_month": int(p.days_in_month),
            "gsc_until": mt.gsc_data_until},
}
with open(os.path.join(ROOT, "dashboard_data.json"), "w") as f:
    json.dump(out, f, separators=(",", ":"))
print("dashboard_data.json written")
