"""
Checks the SQL marts against independent pandas calculations on the raw CSVs.

    python data_generator/generate.py
    python scripts/run_local.py
    python tests/test_marts.py          # or: pytest tests/

Each test recomputes a mart value from the raw data without using the SQL,
then compares it with what the SQL produced.
"""
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import run_local  # noqa: E402

DB = os.path.join(ROOT, "seo_platform.db")


def _con():
    if not os.path.exists(DB):
        run_local.main()
    return sqlite3.connect(DB)


def _raw(name, dates):
    return pd.read_csv(os.path.join(ROOT, "data", f"{name}.csv"), parse_dates=dates)


def test_monthly_organic_new_customers():
    raw = _raw("raw_snowflake_commercial_daily", ["date"])
    org = raw[raw.channel == "organic"].assign(month=lambda d: d.date.dt.strftime("%Y-%m-01"))
    expected = org.groupby(["site_id", "month"]).new_customers.sum()
    got = pd.read_sql("SELECT site_id, month, organic_new_customers FROM mart_site_monthly", _con()) \
        .set_index(["site_id", "month"]).organic_new_customers
    assert (expected == got.reindex(expected.index)).all()


def test_totals_preserved():
    raw = _raw("raw_snowflake_commercial_daily", ["date"])
    got = pd.read_sql("SELECT SUM(total_new_customers) n, SUM(total_net_revenue_eur) r FROM mart_site_monthly", _con()).iloc[0]
    assert got.n == raw.new_customers.sum()
    assert abs(got.r - raw.net_revenue_eur.sum()) < 1


def test_yoy_and_mom():
    m = pd.read_sql("""SELECT site_id, month, organic_new_customers, organic_new_customers_mom,
                       organic_new_customers_yoy FROM mart_site_monthly""", _con())
    m["month"] = pd.to_datetime(m.month)
    piv = m.pivot(index="month", columns="site_id", values="organic_new_customers")
    mom = (piv / piv.shift(1) - 1).stack().rename("exp_mom")
    yoy = (piv / piv.shift(12) - 1).stack().rename("exp_yoy")
    chk = m.set_index(["month", "site_id"]).join(mom).join(yoy).dropna(subset=["exp_mom"])
    assert np.allclose(chk.organic_new_customers_mom, chk.exp_mom)
    chk = chk.dropna(subset=["exp_yoy"])
    assert np.allclose(chk.organic_new_customers_yoy, chk.exp_yoy)


def test_mtd_windows_per_source():
    con = _con()
    raw = _raw("raw_snowflake_commercial_daily", ["date"])
    gsc = _raw("raw_gsc_site_daily", ["data_date"])
    end_c, end_g = raw.date.max(), gsc.data_date.max()
    mtd = pd.read_sql("SELECT * FROM mart_mtd_comparison", con).set_index("site_id")

    def window(df, col, end, prev):
        start = end.replace(day=1)
        if prev:
            start = (start - pd.offsets.MonthBegin(1))
            end = end - pd.DateOffset(months=1)      # clamps to month end like BigQuery
        return df[(df[col] >= start) & (df[col] <= end)]

    org = raw[raw.channel == "organic"]
    for sid, row in mtd.iterrows():
        o = org[org.site_id == sid]
        g = gsc[gsc.site_id == sid]
        assert row.organic_new_customers_mtd == window(o, "date", end_c, False).new_customers.sum()
        assert row.organic_new_customers_prev_mtd == window(o, "date", end_c, True).new_customers.sum()
        assert row.gsc_clicks_mtd == window(g, "data_date", end_g, False).clicks.sum()
        assert row.gsc_clicks_prev_mtd == window(g, "data_date", end_g, True).clicks.sum()
    assert mtd.commercial_data_until.iloc[0] == str(end_c.date())
    assert mtd.gsc_data_until.iloc[0] == str(end_g.date())


def test_target_pacing_forecast():
    p = pd.read_sql("SELECT * FROM mart_target_pacing", _con())
    exp = p.new_customers_mtd / p.days_elapsed * p.days_in_month
    assert np.allclose(p.customers_run_rate_forecast, exp)
    exp_rem = (p.customers_target - p.new_customers_mtd).clip(lower=0)
    assert (p.customers_remaining == exp_rem).all()
    status = np.where(exp >= p.customers_target, "On track",
                      np.where(exp >= 0.9 * p.customers_target, "At risk", "Behind"))
    assert (p.customers_status == status).all()


def test_brand_split():
    raw = _raw("raw_gsc_site_daily", ["data_date"])
    m = pd.read_sql("""SELECT SUM(gsc_clicks) t, SUM(gsc_brand_clicks) b, SUM(gsc_nonbrand_clicks) nb,
                       SUM(nonbrand_traffic_value_eur) v FROM mart_site_monthly""", _con()).iloc[0]
    assert m.b == raw[raw.query_group == "brand"].clicks.sum()
    assert m.nb == raw[raw.query_group == "non_brand"].clicks.sum()
    assert m.t == m.b + m.nb
    cpc = _raw("dim_site", []).set_index("site_id").avg_cpc_eur
    nb = raw[raw.query_group == "non_brand"].groupby("site_id").clicks.sum()
    assert abs(m.v - (nb * cpc).sum()) < 1


def test_channel_targets_and_pacing_rollup():
    con = _con()
    t = _raw("raw_targets_monthly", ["month"])
    p = pd.read_sql("SELECT * FROM mart_target_pacing", con)
    cur = t[t.month == pd.Timestamp(p.month_start.iloc[0])]
    assert len(p) == len(cur)
    assert p.customers_target.sum() == cur.new_customers_target.sum()
    m = pd.read_sql("SELECT month, SUM(new_customers_target_organic) o FROM mart_site_monthly GROUP BY month", con)
    exp = t[t.channel == "organic"].groupby(t.month.dt.strftime("%Y-%m-%d")).new_customers_target.sum()
    assert (m.set_index("month").o == exp.reindex(m.month).values).all()


def test_keyword_distribution():
    r = _raw("raw_rank_tracker_weekly", ["check_date"])
    k = pd.read_sql("SELECT * FROM mart_keyword_positions", _con())
    assert (k.pos_1_3 + k.pos_4_10 + k.pos_11_20 + k.pos_21_100 + k.not_ranking == k.keywords_tracked).all()
    last = r[r.check_date == r.check_date.max()]
    nb = last[last.keyword_group != "brand"]
    km = k[(k.month == k.month.max()) & (k.keyword_group != "brand")]
    assert km.pos_1_3.sum() == nb.position.between(1, 3).sum()
    assert km.not_ranking.sum() == nb.position.isna().sum()


def test_tech_health_score_bounds():
    h = pd.read_sql("SELECT tech_health_score FROM mart_technical_health", _con())
    assert h.tech_health_score.between(0, 100).all()


def test_month_end_clamp():
    assert run_local.udf_date_add("2026-03-31", -1, "MONTH") == "2026-02-28"
    assert run_local.udf_date_add("2024-03-31", -1, "MONTH") == "2024-02-29"
    assert run_local.udf_date_trunc("2026-09-27", "ISOWEEK") == "2026-09-21"


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
