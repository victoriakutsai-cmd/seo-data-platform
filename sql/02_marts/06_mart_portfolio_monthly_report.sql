-- Portfolio monthly report: all sites side by side (the shared monthly doc).
-- Commercial KPIs (new customers, transactions, payments, gross & net revenue,
-- LTV) + organic target + link-building budget usage + toxicity + Core Web Vitals.
CREATE OR REPLACE TABLE `seo_platform.mart_portfolio_monthly_report`
CLUSTER BY site_id
AS
WITH commercial AS (
  SELECT
    site_id,
    DATE_TRUNC(date, MONTH)  AS month,
    SUM(clicks)              AS clicks,
    SUM(signups)             AS signups,
    SUM(new_customers)       AS new_customers,
    SUM(CASE WHEN channel = 'organic' THEN new_customers ELSE 0 END) AS organic_new_customers,
    SUM(transactions)        AS transactions,
    SUM(payments_eur)        AS payments_eur,
    SUM(refunds_eur)         AS refunds_eur,
    SUM(gross_revenue_eur)   AS gross_revenue_eur,
    SUM(promo_cost_eur)      AS promo_cost_eur,
    SUM(net_revenue_eur)     AS net_revenue_eur
  FROM `seo_platform.stg_commercial_daily`
  GROUP BY site_id, DATE_TRUNC(date, MONTH)
),
ltv AS (
  -- LTV proxy: trailing-12-month net revenue per new customer
  SELECT
    site_id, month,
    SUM(net_revenue_eur) OVER (PARTITION BY site_id ORDER BY month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS net_revenue_ttm_eur,
    SUM(new_customers)   OVER (PARTITION BY site_id ORDER BY month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS new_customers_ttm
  FROM commercial
),
cwv AS (
  SELECT
    site_id,
    DATE_TRUNC(check_date, MONTH)  AS month,
    AVG(lcp_ms)                    AS mobile_lcp_ms,
    AVG(inp_ms)                    AS mobile_inp_ms,
    AVG(cls)                       AS mobile_cls,
    AVG(performance_score)         AS mobile_performance_score,
    AVG(cwv_pass)                  AS mobile_cwv_pass_rate
  FROM `seo_platform.stg_cwv_weekly`
  WHERE strategy = 'mobile'
  GROUP BY site_id, DATE_TRUNC(check_date, MONTH)
)
SELECT
  s.site_id, s.brand, s.vertical, s.geo, s.market, s.project,
  c.month,
  c.clicks, c.signups, c.new_customers, c.organic_new_customers,
  c.transactions, c.payments_eur, c.refunds_eur,
  c.gross_revenue_eur, c.promo_cost_eur, c.net_revenue_eur,
  SAFE_DIVIDE(c.net_revenue_eur, c.gross_revenue_eur)          AS net_to_gross,
  SAFE_DIVIDE(c.payments_eur, c.transactions)                  AS avg_transaction_value_eur,
  SAFE_DIVIDE(l.net_revenue_ttm_eur, l.new_customers_ttm)      AS ltv_proxy_eur,
  t.new_customers_target_organic,
  SAFE_DIVIDE(c.organic_new_customers, t.new_customers_target_organic) AS organic_target_achievement,
  b.seo_budget_eur,
  b.links_budget_eur,
  lk.links_spend_eur,
  SAFE_DIVIDE(lk.links_spend_eur, b.links_budget_eur)          AS links_budget_usage,
  lk.new_links_built,
  SAFE_DIVIDE(lk.links_spend_eur, lk.new_links_built)          AS cost_per_link_eur,
  lk.referring_domains,
  lk.domains_toxicity_low, lk.domains_toxicity_medium, lk.domains_toxicity_high,
  SAFE_DIVIDE(lk.domains_toxicity_high, lk.referring_domains)  AS toxic_domains_share,
  v.mobile_lcp_ms, v.mobile_inp_ms, v.mobile_cls, v.mobile_performance_score, v.mobile_cwv_pass_rate
FROM commercial c
JOIN `seo_platform.dim_site` s ON s.site_id = c.site_id
LEFT JOIN ltv l  ON l.site_id = c.site_id AND l.month = c.month
LEFT JOIN (
  SELECT site_id, DATE(month) AS month,
         SUM(CASE WHEN channel = 'organic' THEN new_customers_target ELSE 0 END) AS new_customers_target_organic
  FROM `seo_platform.raw_targets_monthly` GROUP BY site_id, DATE(month)
) t
  ON t.site_id = c.site_id AND t.month = c.month
LEFT JOIN `seo_platform.raw_budgets_monthly` b
  ON b.site_id = c.site_id AND DATE(b.month) = c.month
LEFT JOIN `seo_platform.raw_links_monthly` lk
  ON lk.site_id = c.site_id AND DATE(lk.month) = c.month
LEFT JOIN cwv v  ON v.site_id = c.site_id AND v.month = c.month;
