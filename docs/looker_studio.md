# Looker Studio dashboard: build guide

How to build the dashboard from the `mart_*` tables in Looker Studio. The [live demo](https://victoriakutsai-cmd.github.io/seo-data-platform/) shows the target layout.

## Data sources
| Data source | Table | Date field |
|---|---|---|
| Daily | `mart_site_daily` | `date` |
| Monthly | `mart_site_monthly` | `month` |
| MTD | `mart_mtd_comparison` | (none) |
| Pacing | `mart_target_pacing` | (none) |
| Portfolio | `mart_portfolio_monthly_report` | `month` |
| Keywords | `mart_keyword_rankings` | `month` |

Recalculate ratios as **calculated fields** so they stay correct after aggregation:
`Click → sign-up = SUM(signups) / SUM(clicks)`, `Sign-up → customer = SUM(new_customers) / SUM(signups)`, `Click → customer = SUM(new_customers) / SUM(clicks)`.

## Pages
1. **Overview**: target card (achieved %, left to target, run rate, needed per day, forecast, status) next to KPI scorecards with comparison: new customers, net revenue, clicks, sign-ups, CR, C2S, S2C.
2. **Targets**: progress bars per brand, then per site after a brand is selected (`mart_target_pacing`, summed and ratios recomputed).
3. **Performance over time**: monthly stacked bars by channel with a target line; daily current vs previous month.
4. **Organic search**: brand vs non-brand clicks, non-brand traffic value, keyword position distribution (`mart_keyword_positions`).
5. **Technical health**: health score, CWV, indexation, 4xx / 5xx, uptime per site (`mart_technical_health`).

## Controls
- Filters: `brand`, `geo`, `site_id`, `channel`, `vertical`
- Date range control with **comparison period** (previous period / previous year), so any season can be compared with another.
