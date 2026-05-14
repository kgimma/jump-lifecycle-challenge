-- Claude helped with this page. I was doing checks as I was going in explore.py. 
-- You'll see me reference it often along the way. In the interest of time I had Claude clean up the queries I did into something a bit more organized. 
-- The read me says to do at least 5 checks, so we've got 6 here as a bonus. 
-- On the job this would be more thoughtfully written out by me, but I'm running out of time for the parameters of the challenge. 
-- A result with rows indicates a potential data quality issue.







-- ── Check 1: Billing accounts with no app account match ──────────────────────
-- Why it matters: these accounts have ARR but no usage signals
-- Result: 17,159 billing accounts have no matching app account
-- These are included in the mart with null usage/adoption signals
select count(*) as billing_accounts_without_app_account
from stg_billing_accounts ba
left join stg_app_accounts aa on ba.billing_account_bridge_id = aa.billing_account_bridge_id
where aa.app_account_id is null;

-- ── Check 2: Duplicate billing_account_id + app_account_id combinations ──────
-- Why it matters: duplicates would cause fan-out in downstream joins
-- Result: 22,537 unique combinations confirmed -- no duplicates
select
    billing_account_id,
    app_account_id,
    count(*) as ct
from int_account_bridge
group by 1, 2
having count(*) > 1;

-- ── Check 3: Accounts with multiple churn events (resurrection churn) ─────────
-- Why it matters: our churn logic uses first churn month -- multiple churns are not fully captured
-- Result: 17 accounts churned more than once
select
    billing_account_id,
    count(distinct snapshot_month) as churn_months,
    min(snapshot_month) as first_churn_month,
    max(snapshot_month) as last_churn_month
from mart_account_lifecycle_monthly
where arr_movement_type = 'churned'
group by 1
having count(distinct snapshot_month) > 1
order by 2 desc;

-- ── Check 4: Usage after ARR hits zero ───────────────────────────────────────
-- Why it matters: accounts should not have usage after billing ends
-- Result: usage after churn exists -- likely grace periods or data misalignment
-- Excluded from retention analysis queries
select
    billing_account_id,
    snapshot_month,
    ending_arr,
    total_activity,
    active_user_rate,
    arr_movement_type
from mart_account_lifecycle_monthly
where ending_arr = 0
  and total_activity > 0
order by billing_account_id, snapshot_month
limit 20;

-- ── Check 5: Zero usage retained accounts ────────────────────────────────────
-- Why it matters: accounts paying but not using are high churn risk hiding as retained
-- Result: 24.3% of retained accounts had zero activity in last 3 months
with churned_accounts as (
    select billing_account_id
    from mart_account_lifecycle_monthly
    where arr_movement_type = 'churned'
    group by 1
),
retained_last_3 as (
    select
        billing_account_id,
        sum(total_activity) as total_activity_last_3_months
    from mart_account_lifecycle_monthly
    where billing_account_id not in (select billing_account_id from churned_accounts)
      and is_new_account = 0
      and snapshot_month >= date_trunc('month', current_date) - interval '3 months'
    group by 1
)
select
    case when total_activity_last_3_months = 0 then 'zero activity' else 'has activity' end as activity_status,
    count(distinct billing_account_id) as accounts,
    round(count(distinct billing_account_id) * 100.0 / sum(count(distinct billing_account_id)) over (), 1) as pct_of_total
from retained_last_3
group by 1
order by 1;

-- ── Check 6: Multiple ARR movement types in same month ───────────────────────
-- Why it matters: an account should only have one movement type per month
-- Result: empty -- no accounts had multiple movement types in the same month
with monthly as (
    select
        billing_account_id,
        date_trunc('month', date) as snapshot_month,
        min(starting_arr) as starting_arr,
        max(ending_arr) as ending_arr
    from stg_arr_daily
    where billing_account_id is not null
    group by 1, 2
),
movements as (
    select
        billing_account_id,
        snapshot_month,
        case
            when ending_arr = 0 and starting_arr > 0 then 'churned'
            when ending_arr > starting_arr then 'expansion'
            when ending_arr < starting_arr then 'contraction'
            when ending_arr = starting_arr then 'stable'
            else 'unknown'
        end as arr_movement_type
    from monthly
)
select
    billing_account_id,
    count(distinct arr_movement_type) as distinct_movement_types
from movements
where arr_movement_type != 'stable'
group by 1
having count(distinct arr_movement_type) > 1
order by 2 desc;