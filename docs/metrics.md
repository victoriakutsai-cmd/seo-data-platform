# Metric definitions

The model uses neutral names so it fits any business with a sign-up → first-purchase funnel.

| Metric | Definition | E-commerce | SaaS / subscription | Fintech |
|---|---|---|---|---|
| `clicks` | Visits attributed to a channel | sessions / clicks | sessions | sessions |
| `signups` | Accounts created | account created | trial started | account opened |
| `new_customers` | First paying action | first order | first paid plan | first funded account |
| `transactions` | Paid transactions | orders | invoices / renewals | payments |
| `gross_revenue_eur` | Payments minus refunds | revenue after refunds | billed revenue | fee revenue |
| `net_revenue_eur` | Gross revenue minus promo cost, VAT and payment fees | net revenue | net revenue | net revenue |
| `ltv_proxy_eur` | Trailing 12-month net revenue ÷ new customers in the same 12 months | customer LTV | LTV | LTV |

## Conversion rates

The same three rates for every channel, so channels can be compared directly.

| Rate | Formula | Also known as |
|---|---|---|
| **C2S** · click → sign-up | `SUM(signups) / SUM(clicks)` | visit-to-lead, registration rate |
| **S2C** · sign-up → customer | `SUM(new_customers) / SUM(signups)` | lead-to-customer, activation rate |
| **CR** · click → customer | `SUM(new_customers) / SUM(clicks)` | conversion rate |

## Other ratios

| Ratio | Formula |
|---|---|
| Target achievement | organic `new_customers` ÷ monthly organic target |
| Links budget usage | `links_spend_eur / links_budget_eur` |
| Brand CTR | brand clicks ÷ brand impressions |
| Non-brand share | non-brand clicks ÷ all organic search clicks |
| Non-brand traffic value | non-brand clicks × average CPC of the site |
| Toxic domains share | high-toxicity referring domains ÷ all referring domains |

Ratios are always recalculated from summed numerators and denominators, never averaged, so they stay correct for any filter.

## Channels

One channel list across commercial data, GA4 and targets:

| Channel | Code | Typical sources |
|---|---|---|
| Organic | `organic` | Google / Bing organic search |
| Direct | `direct` | direct visits, bookmarks, brand type-ins |
| Paid media | `paid` | paid search, display, paid social |
| Partners | `referral` | affiliates, referral partners, comparison sites |
| Social | `social` | organic social |

GA4 default channel groups are mapped to these codes in `stg_ga4_channel_daily`.

## Keyword position buckets

1–3, 4–10, 11–20, 21–100 and not ranking (outside the top 100), from the last rank-tracker check of each month.

## Technical health

0–100 score per site and week: 30 × Core Web Vitals pass + 30 × indexation rate + 25 × error score + 15 × uptime score. See `sql/02_marts/08_mart_technical_health.sql`.
