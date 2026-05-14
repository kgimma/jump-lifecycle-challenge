# Model Design Documentation

Gemini helped me design this page layout. I populated the content.

## Overview
This project follows dbt layered modeling conventions: staging → intermediate → mart → report.
All models are written in SQL and executed via DuckDB through `run.py`.
All reports are in `final.py` so you can run the outputs if you'd like. 
In a prod environment these would be converted to dbt models and deployed to a warehouse like BigQuery and then to a vizualization tool. 

==========================================

## Model DAG

Sources (CSVs)
↓
Staging (1:1 with sources, some basic cleaning)
↓
Intermediate (joins, aggregations, business logic)
↓
Mart (final reporting table)
↓
Reports (final.py, this would be what's actually in the BI tool or whatever you use)

==========================================

## Staging Models

### `stg_billing_accounts`
- **Grain:** one row per billing_account_id
- **Primary key:** billing_account_id
- **Source:** billing_accounts.csv
- **Logic:** selects all columns, filters null billing_account_ids

### `stg_app_accounts`
- **Grain:** one row per app_account_id
- **Primary key:** app_account_id
- **Source:** app_accounts.csv
- **Logic:** selects all columns, filters null app_account_ids and internal accounts (is_internal_account = false)

### `stg_app_users`
- **Grain:** one row per app_user_id
- **Primary key:** app_user_id
- **Source:** app_users.csv
- **Logic:** selects all columns, filters null app_user_ids and internal users (is_internal_user = false)

### `stg_usage_daily`
- **Grain:** one row per app_user_id per date
- **Primary key:** app_user_id + date
- **Source:** app_usage_daily.csv
- **Logic:** selects all columns, adds total_activity as sum of all event types, filters null user_ids and dates

### `stg_arr_daily`
- **Grain:** one row per billing_account_id per date
- **Primary key:** billing_account_id + date
- **Source:** arr_daily.csv
- **Logic:** selects all columns, adds arr_change as ending_arr - starting_arr, filters null billing_account_ids and dates

==========================================

## Intermediate Models

### `int_account_bridge`
- **Grain:** one row per billing_account_id + app_account_id combination
- **Primary key:** billing_account_id + app_account_id
- **Sources:** stg_billing_accounts, stg_app_accounts
- **Join key:** billing_account_bridge_id
- **Logic:** left joins billing accounts to app accounts via bridge key. 22,537 rows — 537 more than billing accounts because 259 billing accounts map to more than one app account.
- **Notes:** 17k+ billing accounts have no matching app account

### `int_arr_monthly`
- **Grain:** one row per billing_account_id per snapshot_month
- **Primary key:** billing_account_id + snapshot_month
- **Source:** stg_arr_daily
- **Logic:** aggregates daily ARR to monthly using first/last by date (not min/max) to correctly capture mid-month churn events. Classifies ARR movement as churned, expansion, contraction, or stable.
- **Notes:** almost 20 accounts have multiple churn events (resurrection churn). We use first churn month.

### `int_usage_monthly`
- **Grain:** one row per app_account_id per snapshot_month
- **Primary key:** app_account_id + snapshot_month
- **Sources:** stg_usage_daily, stg_app_users
- **Join key:** app_user_id
- **Logic:** aggregates all daily usage event types to monthly totals per app account. Joins to app_users to get app_account_id.
- **Notes:** Around 200 app accounts had zero usage activity ever and do not appear in this model

### `int_user_adoption_monthly`
- **Grain:** one row per app_account_id per snapshot_month
- **Primary key:** app_account_id + snapshot_month
- **Sources:** stg_app_users, stg_usage_daily
- **Join key:** app_user_id
- **Logic:** calculates active user rate, total/active user counts, owner count, and days-level signals for each feature per app account per month
- **Notes:** active_user_rate is averaged across app accounts when rolled up to billing account level in the mart

==========================================

## Mart Model

### `mart_account_lifecycle_monthly`
- **Grain:** one row per billing_account_id + app_account_id + snapshot_month
- **Primary key:** billing_account_id + app_account_id + snapshot_month
- **Sources:** stg_billing_accounts, stg_arr_daily, int_account_bridge, int_arr_monthly, int_usage_monthly, int_user_adoption_monthly
- **Notes:** grain includes app_account_id because some billing accounts map to multiple app accounts. To get one row per billing account per month, filter to the most active app_account_id or aggregate further.

### CTE Structure
| CTE               | Logic |
| accounts          | Account spine — all billing accounts x all months they appear in ARR data |
| arr_signals       | ARR movement per billing account per month with MoM lag |
| usage_signals     | Usage metrics aggregated from app account to billing account level |
| adoption_signals  | User adoption metrics aggregated from app account to billing account level with MoM lag |
| expansion_signals | Expansion event flags per billing account per month |
| segment_scores    | Joins all signals together with coalesces for nulls |
| final             | Applies lifecycle segment, expansion-ready flag, reason code, and recommended action |

### Known Data Quality Risks

- 17k+ billing accounts have no app account match
  - Impact: These accounts show ARR but no usage signals
  - Mitigation: Included in mart with null usage/adoption signals

- Post-churn usage exists
  - Impact: Inflates churned account activity metrics
  - Mitigation: Analysis queries exclude post-churn months

- Almost 20 accounts have multiple churn events
  - Impact: First churn month used, subsequent churns not captured
  - Mitigation: Documented as caveat. It's kind of it's own lense to look through separately

- active_user_rate averaged across multiple app accounts
  - Impact: May mask variance between app accounts
  - Mitigation: Document and consider weighting by user count in future

- ARR and usage data come from separate systems
  - Impact: Accounts with zero ARR may still show usage
  - Mitigation: Documented as caveat, excluded from retention analysis

- New account window spans 2 calendar months
  - Impact: Some new accounts may appear in 2 months of data
  - Mitigation: Acceptable tradeoff, documented

==========================================

## Production Considerations
- CSV file paths would be converted to `{{ ref('model_name') }}` for dbt compatibility
- Connect to BigQuery via dbt profile if I were on the team
- Schedule via dbt Cloud or Airflow on whatever cadence makes sense for the metric(s)
- Add dbt tests for primary key uniqueness, not-null constraints, and accepted values. Probably send slack alerts
- Consider partitioning for query performance at scale whatever that may look like for growing data