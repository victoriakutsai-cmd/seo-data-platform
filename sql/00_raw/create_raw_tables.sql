-- =============================================================================
-- RAW LAYER (BigQuery) - landing tables, loaded as-is from each source
--   * Snowflake  -> Cloud Storage (daily export) -> BigQuery load job
--   * GSC / GA4 / PSI / Ahrefs / Semrush -> Python API loaders
--   * Targets & budgets -> Google Sheets maintained by SEO / channel leads
--   * Technical audit -> crawler export + GSC indexing + uptime monitor
-- Partitioned by date, clustered by site_id: daily jobs scan only new data.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS `seo_platform`;

CREATE TABLE IF NOT EXISTS `seo_platform.dim_site` (
  site_id STRING NOT NULL, brand STRING, vertical STRING, geo STRING, market STRING,
  currency STRING, domain STRING, project STRING, launch_date DATE,
  fees_rate FLOAT64, avg_cpc_eur FLOAT64,  -- non-brand CPC, values organic traffic
  ga4_property_id STRING
);

-- Brand terms per site (regex), used to split GSC queries into brand / non-brand
CREATE TABLE IF NOT EXISTS `seo_platform.cfg_brand_terms` (
  site_id STRING, brand_regex STRING                       -- e.g. r'brand\s?a|branda'
);

-- Keywords tracked per site (priority + brand), maintained by SEO leads
CREATE TABLE IF NOT EXISTS `seo_platform.cfg_tracked_keywords` (
  site_id STRING, query STRING, keyword_group STRING   -- 'priority' | 'brand'
);

-- Commercial data from Snowflake: one row per site x day x channel
CREATE TABLE IF NOT EXISTS `seo_platform.raw_snowflake_commercial_daily` (
  site_id STRING, date DATE, channel STRING,
  clicks INT64, signups INT64, new_customers INT64, active_customers INT64,
  transactions INT64, payments_eur NUMERIC, refunds_eur NUMERIC,
  gross_revenue_eur NUMERIC, promo_cost_eur NUMERIC, net_revenue_eur NUMERIC
)
PARTITION BY date
CLUSTER BY site_id;

-- Google Search Console, split into brand / non-brand queries.
-- query_group is assigned at load time by matching queries against each
-- site's brand terms (cfg_brand_terms); anonymized queries count as non_brand.
CREATE TABLE IF NOT EXISTS `seo_platform.raw_gsc_site_daily` (
  site_id STRING, data_date DATE, search_type STRING,
  query_group STRING,                                      -- 'brand' | 'non_brand'
  clicks INT64, impressions INT64, sum_position FLOAT64   -- zero-based, like bulk export
)
PARTITION BY data_date
CLUSTER BY site_id;

-- Google Search Console (priority + brand keywords)
CREATE TABLE IF NOT EXISTS `seo_platform.raw_gsc_keyword_daily` (
  site_id STRING, data_date DATE, query STRING, keyword_group STRING,
  impressions INT64, clicks INT64, avg_position FLOAT64
)
PARTITION BY data_date
CLUSTER BY site_id, keyword_group;

-- GA4 Data API (sessions by default channel group)
CREATE TABLE IF NOT EXISTS `seo_platform.raw_ga4_channel_daily` (
  site_id STRING, date DATE, session_default_channel_group STRING,
  sessions INT64, engaged_sessions INT64, sign_up_events INT64
)
PARTITION BY date
CLUSTER BY site_id;

-- Targets per site x month x channel (Google Sheet maintained by SEO / channel leads)
CREATE TABLE IF NOT EXISTS `seo_platform.raw_targets_monthly` (
  site_id STRING, month DATE, channel STRING,
  new_customers_target INT64, net_revenue_target_eur NUMERIC
);

-- SEO budgets per site x month
CREATE TABLE IF NOT EXISTS `seo_platform.raw_budgets_monthly` (
  site_id STRING, month DATE,
  organic_clicks_target INT64, seo_budget_eur NUMERIC, links_budget_eur NUMERIC
);

-- Ahrefs / Semrush: link building & toxicity
CREATE TABLE IF NOT EXISTS `seo_platform.raw_links_monthly` (
  site_id STRING, month DATE, tool STRING,
  referring_domains INT64, new_links_built INT64, links_spend_eur NUMERIC,
  domains_toxicity_low INT64, domains_toxicity_medium INT64, domains_toxicity_high INT64
);

-- PageSpeed Insights API: Core Web Vitals
CREATE TABLE IF NOT EXISTS `seo_platform.raw_psi_cwv_weekly` (
  site_id STRING, check_date DATE, strategy STRING,
  lcp_ms FLOAT64, inp_ms FLOAT64, cls FLOAT64, performance_score FLOAT64
)
PARTITION BY check_date
CLUSTER BY site_id;

-- Weekly technical audit: crawler + GSC indexing report + uptime monitor
CREATE TABLE IF NOT EXISTS `seo_platform.raw_site_audit_weekly` (
  site_id STRING, check_date DATE,
  pages_submitted INT64, pages_indexed INT64,
  errors_4xx INT64, errors_5xx INT64, broken_internal_links INT64, uptime_pct FLOAT64
)
PARTITION BY check_date
CLUSTER BY site_id;

-- Rank tracker (weekly positions of tracked keywords; NULL = not in top 100)
CREATE TABLE IF NOT EXISTS `seo_platform.raw_rank_tracker_weekly` (
  site_id STRING, check_date DATE, keyword STRING,
  keyword_group STRING,                                    -- 'brand' | 'priority' | 'long_tail'
  position INT64
)
PARTITION BY check_date
CLUSTER BY site_id, keyword_group;
