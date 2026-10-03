"""
Synthetic data generator for the SEO Data Platform portfolio project.

Everything produced here is fictional: brands, domains, volumes, targets and
events. The schema is a generic multi-site SEO reporting design written for
this repository.

Usage:
    python data_generator/generate.py            # writes CSVs to ./data
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

SEED = 42
START = date(2023, 7, 1)
END_COMMERCIAL = date(2026, 9, 29)   # commercial data: complete to D-1
END_GSC = date(2026, 9, 27)          # GSC data lags ~2-3 days
GSC_NUM100_DROP = pd.Timestamp("2025-09-12")  # Google removed &num=100

# Realistic shocks so the dashboards have something to catch:
# (site_id, channel, start, end or None, multiplier, reason)
EVENTS = [
    ("S002", "organic", "2026-09-08", None, 0.72, "core update hit"),
    ("S009", "organic", "2026-09-08", None, 0.78, "core update hit"),
    ("S015", "organic", "2026-09-08", None, 0.80, "core update hit"),
    ("S006", "organic", "2026-09-05", None, 1.22, "core update win"),
    ("S013", "organic", "2026-09-10", None, 1.18, "new content hub"),
    ("S011", "organic", "2026-06-10", "2026-07-31", 0.62, "site migration issues"),
    ("S004", "organic", "2026-03-20", None, 1.15, "March core update win"),
    ("S010", "organic", "2026-03-20", None, 1.12, "March core update win"),
    ("S008", "paid", "2026-08-01", None, 0.55, "paid budget cut"),
    ("S016", "paid", "2026-09-01", None, 0.60, "paid budget cut"),
    ("S012", "referral", "2026-09-12", None, 0.65, "referral partner lost"),
]


LONGTAIL_TEMPLATES = ["{kw} {market}", "best {kw}", "{kw} online", "{kw} prices", "{kw} reviews",
                      "cheap {kw}", "{kw} comparison", "{kw} near me"]

# Technical incidents for the weekly site audit: (site_id, start, end, kind)
AUDIT_EVENTS = [
    ("S011", "2026-06-08", "2026-08-03", "migration"),     # matches the migration traffic dip
    ("S014", "2026-09-07", "2026-09-30", "server"),        # 5xx spike and lower uptime
]


def event_multiplier(site_id: str, channel: str, dates: pd.DatetimeIndex) -> np.ndarray:
    m = np.ones(len(dates))
    for sid, ch, start, end, mult, _ in EVENTS:
        if sid == site_id and ch == channel:
            mask = dates >= pd.Timestamp(start)
            if end:
                mask &= dates <= pd.Timestamp(end)
            m[mask] *= mult
    return m

OUT = os.path.join(os.path.dirname(__file__), "..", "data")
rng = np.random.default_rng(SEED)

# --------------------------------------------------------------------------- #
# Dimensions
# --------------------------------------------------------------------------- #
MARKETS = {
    # geo: (market, currency, VAT & payment fees as share of gross revenue)
    "UK": ("United Kingdom", "GBP", 0.20), "IE": ("Ireland", "EUR", 0.18),
    "DE": ("Germany", "EUR", 0.17),        "NL": ("Netherlands", "EUR", 0.18),
    "PL": ("Poland", "PLN", 0.19),         "ES": ("Spain", "EUR", 0.18),
    "FR": ("France", "EUR", 0.20),           "CA": ("Canada", "CAD", 0.12),
}

# average non-brand CPC by vertical (EUR), used to value non-brand organic clicks
VERTICAL_CPC = {"Travel & booking": 0.90, "Online education": 1.40, "Fintech & payments": 2.80,
                "E-commerce: home & living": 0.70, "Streaming subscription": 1.10}

# brand: (vertical, markets, non-brand priority keywords)
BRANDS = {
    "Alpha": ("Travel & booking", ["UK", "DE", "NL", "ES"],
                ["cheap flights", "hotel deals", "last minute holidays", "city breaks", "travel insurance", "car rental"]),
    "Bravo": ("Online education", ["UK", "PL", "CA"],
                ["online courses", "learn english online", "coding bootcamp", "online certificate", "language app", "exam preparation"]),
    "Charlie": ("Fintech & payments", ["UK", "NL", "FR"],
                ["money transfer", "currency exchange", "business account", "virtual card", "send money abroad", "payment app"]),
    "Delta": ("E-commerce: home & living", ["DE", "PL", "NL"],
                ["sofa", "garden furniture", "kitchen storage", "led lighting", "home decor", "mattress"]),
    "Echo": ("Streaming subscription", ["UK", "IE", "CA"],
                ["streaming service", "watch movies online", "tv series online", "streaming app", "family plan", "free trial streaming"]),
}

CHANNELS = ["organic", "direct", "paid", "referral", "social"]

CHANNEL_PROFILE = {
    # clicks relative to organic, click -> sign-up, sign-up -> new customer
    "organic":  (1.00, 0.070, 0.42),
    "direct":   (0.55, 0.110, 0.50),
    "paid":     (0.80, 0.045, 0.33),
    "referral": (0.60, 0.085, 0.47),
    "social":   (0.35, 0.030, 0.25),
}

# Seasonality and month-to-month volatility are tuned to look like real
# multi-site web traffic: uneven months, a summer dip, an autumn peak.
MONTH_SEASON = {1: 1.00, 2: 0.97, 3: 1.03, 4: 1.06, 5: 0.98, 6: 1.04,
                7: 0.88, 8: 0.90, 9: 0.99, 10: 1.07, 11: 1.08, 12: 1.03}
MONTHLY_NOISE = 0.11      # month-level shocks (log scale) around the trend
WALK_NOISE = 0.04         # slow drift of the trend itself
WEEKDAY = {0: 0.93, 1: 0.92, 2: 0.95, 3: 0.98, 4: 1.06, 5: 1.10, 6: 1.06}


def build_sites() -> pd.DataFrame:
    rows, i = [], 1
    for brand, (vertical, geos, _) in BRANDS.items():
        for geo in geos:
            market, cur, fee = MARKETS[geo]
            rows.append({
                "site_id": f"S{i:03d}",
                "brand": brand,
                "vertical": vertical,
                "geo": geo,
                "market": market,
                "currency": cur,
                "domain": f"{brand.lower().replace(' ', '-')}-{geo.lower()}.example",
                "project": "Portfolio A",
                "launch_date": str(START),
                "fees_rate": fee,
                "avg_cpc_eur": round(VERTICAL_CPC[vertical] * rng.uniform(0.8, 1.25), 2),
                "ga4_property_id": str(400000000 + i),
            })
            i += 1
    return pd.DataFrame(rows)


def site_curve(dates: pd.DatetimeIndex, base: float, growth: float, noise: float) -> np.ndarray:
    """Daily series = trend x uneven monthly level x seasonality x weekday x daily noise."""
    months = pd.date_range(dates[0], dates[-1] + pd.offsets.MonthBegin(1), freq="MS")
    n = len(months)
    walk = np.cumsum(rng.normal(0, WALK_NOISE, n))
    level = np.log(1 + growth) * np.arange(n) / 12 + walk + rng.normal(0, MONTHLY_NOISE, n)
    # interpolate month levels (anchored mid-month) to days so there are no steps at month edges
    mid = (months + pd.Timedelta(days=14)).values.astype("datetime64[D]").astype(float)
    daily_level = np.interp(dates.values.astype("datetime64[D]").astype(float), mid, level)
    season = dates.month.map(MONTH_SEASON).values
    week = dates.weekday.map(WEEKDAY).values
    eps = rng.lognormal(0, noise, len(dates))
    return base * np.exp(daily_level) * season * week * eps


def drift(dates: pd.DatetimeIndex, trend: float, sigma: float) -> np.ndarray:
    """Slowly moving multiplier (e.g. for conversion rates): yearly trend + monthly random walk."""
    months = pd.date_range(dates[0], dates[-1] + pd.offsets.MonthBegin(1), freq="MS")
    lvl = np.log(1 + trend) * np.arange(len(months)) / 12 + np.cumsum(rng.normal(0, sigma, len(months)))
    mid = (months + pd.Timedelta(days=14)).values.astype("datetime64[D]").astype(float)
    return np.exp(np.interp(dates.values.astype("datetime64[D]").astype(float), mid, lvl))


def generate():
    os.makedirs(OUT, exist_ok=True)
    sites = build_sites()
    dates = pd.date_range(START, END_COMMERCIAL, freq="D")
    gsc_dates = pd.date_range(START, END_GSC, freq="D")

    commercial, gsc, gsc_kw, ga4 = [], [], [], []
    budgets, targets, links, cwv, audit, ranks = [], [], [], [], [], []
    months = pd.date_range(START, "2026-12-01", freq="MS")
    dim_last = pd.Timestamp(END_COMMERCIAL).days_in_month
    elapsed_last = pd.Timestamp(END_COMMERCIAL).day

    for s in sites.itertuples():
        # Organic search = brand demand + non-brand (SEO) demand, each with its own dynamics
        base = rng.uniform(300, 4000)                      # organic search clicks / day at start
        brand_share = rng.uniform(0.45, 0.75)
        n = len(gsc_dates)
        brand = site_curve(dates, base * brand_share, rng.uniform(0.08, 0.35), 0.10)
        nonbrand = site_curve(dates, base * (1 - brand_share), rng.uniform(0.15, 0.60), 0.14) \
            * event_multiplier(s.site_id, "organic", dates)
        search = brand + nonbrand

        # ---------------- commercial (Snowflake) ----------------
        for ch in CHANNELS:
            share, c2s, s2c = CHANNEL_PROFILE[ch]
            c2s *= rng.uniform(0.8, 1.2)
            s2c *= rng.uniform(0.85, 1.15)
            if ch == "organic":
                traffic = search * rng.uniform(0.75, 0.9)          # tracked visits from organic search
            else:
                traffic = site_curve(dates, base * share * 0.8, rng.uniform(0.0, 0.40), 0.12) \
                    * event_multiplier(s.site_id, ch, dates)
            clicks = np.round(traffic).astype(int)
            # conversion rates move over time (UX changes, offers, traffic mix)
            c2s_t = np.clip(c2s * drift(dates, rng.uniform(-0.05, 0.15), 0.045), 0.005, 0.5)
            s2c_t = np.clip(s2c * drift(dates, rng.uniform(-0.05, 0.10), 0.035), 0.05, 0.9)
            signups = rng.binomial(clicks, c2s_t)
            new_cust = rng.binomial(signups, s2c_t)
            # active customers ~ rolling base of new customers who keep buying
            active = np.round(pd.Series(new_cust).rolling(60, min_periods=1).sum().values * 0.55 + new_cust).astype(int)
            transactions = np.round(active * rng.uniform(0.35, 0.55, len(dates))).astype(int)
            payments = np.round(transactions * rng.normal(48, 6, len(dates)), 2)
            refunds = np.round(payments * rng.uniform(0.04, 0.09, len(dates)), 2)
            gross = np.round((payments - refunds) * rng.uniform(0.85, 0.95, len(dates)), 2)
            promo = np.round(gross * rng.uniform(0.08, 0.16, len(dates)), 2)
            net = np.round(gross - promo - gross * s.fees_rate, 2)

            df = pd.DataFrame({"site_id": s.site_id, "date": dates.date, "channel": ch,
                               "clicks": clicks, "signups": signups, "new_customers": new_cust,
                               "active_customers": active, "transactions": transactions,
                               "payments_eur": payments, "refunds_eur": refunds,
                               "gross_revenue_eur": gross, "promo_cost_eur": promo,
                               "net_revenue_eur": net})
            commercial.append(df)

            # Targets per channel: a YoY growth plan on the same month last year
            # (first year: planned close to the forecast). Set before the month starts,
            # so shocks during the month show up as misses.
            mon = df.assign(m=pd.to_datetime(df.date).dt.to_period("M")).groupby("m")[["new_customers", "net_revenue_eur"]].sum().astype(float)
            mon.iloc[-1] = mon.iloc[-1] * dim_last / elapsed_last          # current month -> full-month estimate
            plan = {y: rng.uniform(1.22, 1.52) for y in (2024, 2025, 2026)}
            for m in months:
                per = m.to_period("M")
                if m < pd.Timestamp(START) + pd.DateOffset(years=1):     # first year: no history yet
                    base_n, base_r, g = mon.loc[per, "new_customers"], mon.loc[per, "net_revenue_eur"], rng.uniform(0.92, 1.12)
                else:
                    ly = (m - pd.DateOffset(years=1)).to_period("M")
                    base_n, base_r, g = mon.loc[ly, "new_customers"], mon.loc[ly, "net_revenue_eur"], plan[m.year] * rng.uniform(0.95, 1.05)
                targets.append({"site_id": s.site_id, "month": m.date(), "channel": ch,
                                "new_customers_target": int(round(base_n * g)),
                                "net_revenue_target_eur": round(base_r * g * rng.uniform(0.97, 1.03), 0)})

        # ---------------- GSC: brand vs non-brand queries ----------------
        after = gsc_dates >= GSC_NUM100_DROP
        for group, series, ctr_mu, pos_mu in [("brand", brand, 0.42, 1.6), ("non_brand", nonbrand, 0.028, 17.0)]:
            g_clicks = np.round(series[:n] * rng.uniform(1.15, 1.35)).astype(int)
            ctr = np.clip(rng.normal(ctr_mu, ctr_mu * 0.08, n), 0.005, 0.8)
            impr = np.round(g_clicks / ctr).astype(int)
            pos = np.clip(rng.normal(pos_mu, pos_mu * 0.07, n), 1, 60)
            if group == "non_brand":                    # &num=100 removal: bot impressions disappear
                impr[after] = np.round(impr[after] * 0.55).astype(int)
                pos[after] = pos[after] * 0.70
            gsc.append(pd.DataFrame({"site_id": s.site_id, "data_date": gsc_dates.date,
                                     "search_type": "web", "query_group": group,
                                     "clicks": g_clicks, "impressions": impr,
                                     # GSC bulk export stores zero-based sum of positions
                                     "sum_position": np.round((pos - 1) * impr, 1)}))

        # ---------------- GSC keyword positions ----------------
        kws = [(k, "priority") for k in BRANDS[s.brand][2]] + \
              [(s.brand, "brand"), (f"{s.brand} app", "brand"), (f"{s.brand} {s.market}", "brand")]
        for kw, kind in kws:
            start_pos = rng.uniform(1, 2.5) if kind == "brand" else rng.uniform(8, 45)
            end_pos = 1.0 if kind == "brand" else max(1, start_pos * rng.uniform(0.25, 1.1))
            path = np.linspace(start_pos, end_pos, n) + rng.normal(0, 0.8 if kind == "brand" else 2.2, n)
            path = np.clip(path, 1, 100)
            kw_impr = np.round(rng.lognormal(5 if kind == "priority" else 4, 0.3, n)).astype(int)
            gsc_kw.append(pd.DataFrame({"site_id": s.site_id, "data_date": gsc_dates.date,
                                        "query": kw.lower(), "keyword_group": kind,
                                        "impressions": kw_impr,
                                        "clicks": np.round(kw_impr * np.clip(0.35 / path, 0.002, 0.6)).astype(int),
                                        "avg_position": np.round(path, 1)}))

        # ---------------- GA4 ----------------
        for ch in CHANNELS:
            ga_name = {"organic": "Organic Search", "direct": "Direct", "paid": "Paid Search",
                       "referral": "Referral", "social": "Organic Social"}[ch]
            share = CHANNEL_PROFILE[ch][0]
            sess = np.round(search * share * rng.uniform(1.6, 2.2) * rng.lognormal(0, 0.07, len(dates))).astype(int)
            ga4.append(pd.DataFrame({"site_id": s.site_id, "date": dates.date,
                                     "session_default_channel_group": ga_name, "sessions": sess,
                                     "engaged_sessions": np.round(sess * rng.uniform(0.5, 0.68, len(dates))).astype(int),
                                     "sign_up_events": np.round(sess * CHANNEL_PROFILE[ch][1] * 0.45).astype(int)}))

        # ---------------- monthly targets, budgets, links ----------------
        ref_domains = int(rng.uniform(300, 1800))
        for m in months:
            mask = (dates.year == m.year) & (dates.month == m.month)
            links_budget = float(round(rng.choice([2000, 3000, 4000, 5000, 6000]), 0))
            spend = round(links_budget * rng.uniform(0.6, 1.08), 0) if m <= pd.Timestamp(END_COMMERCIAL) else 0.0
            new_links = int(spend / rng.uniform(180, 320))
            ref_domains += new_links + int(rng.normal(5, 8))
            high = int(ref_domains * rng.uniform(0.02, 0.07))
            med = int(ref_domains * rng.uniform(0.10, 0.20))
            budgets.append({"site_id": s.site_id, "month": m.date(),
                            "organic_clicks_target": int(search[mask].sum() * rng.uniform(0.85, 0.95)) if mask.any() else None,
                            "seo_budget_eur": round(links_budget * rng.uniform(1.8, 2.6), 0),
                            "links_budget_eur": links_budget})
            if m <= pd.Timestamp(END_COMMERCIAL):
                links.append({"site_id": s.site_id, "month": m.date(), "tool": "ahrefs",
                              "referring_domains": ref_domains, "new_links_built": new_links,
                              "links_spend_eur": spend,
                              "domains_toxicity_low": ref_domains - high - med,
                              "domains_toxicity_medium": med, "domains_toxicity_high": high})

        # ---------------- Core Web Vitals (PSI, weekly) ----------------
        weeks = pd.date_range(START, END_COMMERCIAL, freq="W-MON")
        lcp0 = rng.uniform(1900, 3600)
        for strategy, mult in [("mobile", 1.0), ("desktop", 0.55)]:
            lcp = np.clip(np.linspace(lcp0, lcp0 * rng.uniform(0.6, 1.05), len(weeks)) * mult
                          + rng.normal(0, 180, len(weeks)), 700, 8000)
            inp = np.clip(rng.normal(190 * mult, 45, len(weeks)), 40, 700)
            cls = np.clip(rng.normal(0.08, 0.04, len(weeks)), 0, 0.5)
            score = np.clip(100 - (lcp - 1200) / 45 - (inp - 100) / 12 - cls * 80, 5, 100)
            cwv.append(pd.DataFrame({"site_id": s.site_id, "check_date": weeks.date,
                                     "strategy": strategy, "lcp_ms": lcp.round(0),
                                     "inp_ms": inp.round(0), "cls": cls.round(3),
                                     "performance_score": score.round(0)}))

        # ---------------- rank tracker (weekly, ~57 tracked keywords per site) ----------------
        kw_set = [(s.brand.lower(), "brand"), (f"{s.brand.lower()} app", "brand"), (f"{s.brand.lower()} {s.market.lower()}", "brand")]
        for kw in BRANDS[s.brand][2]:
            kw_set.append((kw, "priority"))
            kw_set += [(t.format(kw=kw, market=s.market.lower()), "long_tail") for t in LONGTAIL_TEMPLATES]
        ev = {e[0]: e for e in EVENTS if e[1] == "organic"}
        for kw, grp in kw_set:
            if grp == "brand":
                pos = np.clip(rng.normal(1.3, 0.4, len(weeks)), 1, 4)
            else:
                start = rng.uniform(3, 60) if grp == "long_tail" else rng.uniform(5, 35)
                end = max(1.0, start * rng.uniform(0.18, 0.8))            # most keywords improve over time
                pos = np.exp(np.linspace(np.log(start), np.log(end), len(weeks)) + rng.normal(0, 0.12, len(weeks)))
                if s.site_id in ev:                                          # core update / migration effects
                    _, _, st, en, mult, _ = ev[s.site_id]
                    mk = weeks >= pd.Timestamp(st)
                    if en:
                        mk &= weeks <= pd.Timestamp(en)
                    pos[mk] = pos[mk] * (1 / mult) ** 2.2
            pos = np.round(pos).astype(int)
            ranks.append(pd.DataFrame({"site_id": s.site_id, "check_date": weeks.date, "keyword": kw,
                                       "keyword_group": grp,
                                       "position": np.where(pos > 100, None, pos)}))

        # ---------------- technical audit (crawler + GSC indexing, weekly) ----------------
        pages0 = int(rng.uniform(800, 9000))
        submitted = np.round(pages0 * np.linspace(1, rng.uniform(1.1, 1.6), len(weeks))).astype(int)
        idx_ratio = np.clip(rng.uniform(0.78, 0.95) + np.linspace(0, rng.uniform(0, 0.05), len(weeks))
                            + rng.normal(0, 0.01, len(weeks)), 0.5, 0.99)
        e4 = np.round(submitted * rng.uniform(0.002, 0.012) * rng.lognormal(0, 0.3, len(weeks))).astype(int)
        e5 = rng.poisson(rng.uniform(0.2, 3), len(weeks))
        broken = np.round(submitted * rng.uniform(0.001, 0.006) * rng.lognormal(0, 0.3, len(weeks))).astype(int)
        uptime = np.clip(rng.normal(99.92, 0.05, len(weeks)), 99.0, 100.0)
        for sid, start, end, kind in AUDIT_EVENTS:
            if sid != s.site_id:
                continue
            mk = (weeks >= pd.Timestamp(start)) & (weeks <= pd.Timestamp(end))
            if kind == "migration":
                idx_ratio[mk] *= 0.72; e4[mk] *= 6; broken[mk] *= 5
            elif kind == "server":
                e5[mk] += rng.poisson(60, mk.sum()); uptime[mk] -= rng.uniform(0.4, 1.2, mk.sum())
        audit.append(pd.DataFrame({"site_id": s.site_id, "check_date": weeks.date,
                                   "pages_submitted": submitted, "pages_indexed": np.round(submitted * idx_ratio).astype(int),
                                   "errors_4xx": e4, "errors_5xx": e5, "broken_internal_links": broken,
                                   "uptime_pct": uptime.round(3)}))

    out = {
        "dim_site": sites,
        "cfg_brand_terms": pd.DataFrame({"site_id": sites.site_id,
                                         "brand_regex": [rf"{b.lower().replace(' ', r'\s?')}" for b in sites.brand]}),
        "cfg_tracked_keywords": pd.concat(gsc_kw)[["site_id", "query", "keyword_group"]].drop_duplicates(),
        "raw_snowflake_commercial_daily": pd.concat(commercial),
        "raw_gsc_site_daily": pd.concat(gsc),
        "raw_gsc_keyword_daily": pd.concat(gsc_kw),
        "raw_ga4_channel_daily": pd.concat(ga4),
        "raw_targets_monthly": pd.DataFrame(targets),
        "raw_budgets_monthly": pd.DataFrame(budgets).astype({"organic_clicks_target": "Int64"}),
        "raw_site_audit_weekly": pd.concat(audit),
        "raw_rank_tracker_weekly": pd.concat(ranks).astype({"position": "Int64"}),
        "raw_links_monthly": pd.DataFrame(links),
        "raw_psi_cwv_weekly": pd.concat(cwv),
    }
    for name, df in out.items():
        path = os.path.join(OUT, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"{name:35s} {len(df):>9,d} rows -> {os.path.relpath(path)}")


if __name__ == "__main__":
    generate()
