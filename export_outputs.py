# NOTE: See final.py for notes on the answers to these. It's also writt


import re

conn = duckdb.connect()

def register_view(folder, name):
    sql = open(f'models/{folder}/{name}.sql').read()
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    conn.execute(f'create or replace view {name} as ({sql})')

for name in ['stg_billing_accounts','stg_app_accounts','stg_app_users','stg_usage_daily','stg_arr_daily']:
    register_view('staging', name)
for name in ['int_account_bridge','int_arr_monthly','int_usage_monthly','int_user_adoption_monthly']:
    register_view('intermediate', name)
for name in ['mart_account_lifecycle_monthly']:
    register_view('marts', name)

# ==================================================================== #
# Q1: Which accounts appear healthy, under-adopted, at risk, or expansion-ready?
# Q4: Which accounts appear expansion-ready?
# Q5: Which accounts should Customer Success or GTM prioritize, and why?
# ==================================================================== #
print("exporting Q1, Q4, Q5...")
conn.execute("""
    select
        snapshot_month,
        billing_account_id,
        billing_account_name,
        customer_segment,
        lifecycle_segment,
        is_expansion_ready,
        recommended_action,
        reason_code
    from mart_account_lifecycle_monthly
    order by snapshot_month, billing_account_id
""").df().to_csv('outputs/q1_q4_q5_account_lifecycle_signals.csv', index=False)
print("done: outputs/q1_q4_q5_account_lifecycle_signals.csv")

# ==================================================================== #
# Q2: Which product adoption patterns appear associated with retention?
# Q3: Which product adoption patterns appear before churn or contraction?
# ==================================================================== #
print("exporting Q2, Q3...")
conn.execute("""
    with churned_accounts as (
        select billing_account_id, min(snapshot_month) as churn_month
        from mart_account_lifecycle_monthly
        where arr_movement_type = 'churned'
        group by 1
    ),
    contracted_accounts as (
        select billing_account_id, min(snapshot_month) as contraction_month
        from mart_account_lifecycle_monthly
        where arr_movement_type = 'contraction'
          and billing_account_id not in (select billing_account_id from churned_accounts)
        group by 1
    ),
    retained_activity as (
        select
            billing_account_id,
            sum(total_activity) as total_activity_last_3_months
        from mart_account_lifecycle_monthly
        where billing_account_id not in (select billing_account_id from churned_accounts)
          and billing_account_id not in (select billing_account_id from contracted_accounts)
          and is_new_account = 0
          and snapshot_month >= date_trunc('month', current_date) - interval '3 months'
        group by 1
    ),
    pre_churn as (
        select
            m.billing_account_id,
            m.customer_segment,
            'churned' as retention_status,
            m.active_user_rate,
            m.total_meetings,
            m.total_ai_chats,
            m.days_with_meetings,
            m.days_with_dashboards,
            m.days_with_notes_synced,
            m.days_with_tasks,
            m.total_activity
        from mart_account_lifecycle_monthly m
        join churned_accounts c on m.billing_account_id = c.billing_account_id
        where m.snapshot_month < c.churn_month
          and m.snapshot_month >= c.churn_month - interval '3 months'
          and m.is_new_account = 0
    ),
    pre_contraction as (
        select
            m.billing_account_id,
            m.customer_segment,
            'contracted' as retention_status,
            m.active_user_rate,
            m.total_meetings,
            m.total_ai_chats,
            m.days_with_meetings,
            m.days_with_dashboards,
            m.days_with_notes_synced,
            m.days_with_tasks,
            m.total_activity
        from mart_account_lifecycle_monthly m
        join contracted_accounts c on m.billing_account_id = c.billing_account_id
        where m.snapshot_month < c.contraction_month
          and m.snapshot_month >= c.contraction_month - interval '3 months'
          and m.is_new_account = 0
    ),
    retained as (
        select
            m.billing_account_id,
            m.customer_segment,
            case when ra.total_activity_last_3_months = 0
                then 'retained_inactive'
                else 'retained_active'
            end as retention_status,
            m.active_user_rate,
            m.total_meetings,
            m.total_ai_chats,
            m.days_with_meetings,
            m.days_with_dashboards,
            m.days_with_notes_synced,
            m.days_with_tasks,
            m.total_activity
        from mart_account_lifecycle_monthly m
        join retained_activity ra on m.billing_account_id = ra.billing_account_id
        where m.is_new_account = 0
          and m.snapshot_month >= date_trunc('month', current_date) - interval '3 months'
    )
    select
        customer_segment,
        retention_status,
        round(avg(active_user_rate), 2) as avg_active_user_rate,
        round(avg(total_meetings), 2) as avg_meetings,
        round(avg(total_ai_chats), 2) as avg_ai_chats,
        round(avg(days_with_meetings), 2) as avg_days_with_meetings,
        round(avg(days_with_notes_synced), 2) as avg_days_with_notes_synced,
        round(avg(days_with_tasks), 2) as avg_days_with_tasks,
        round(avg(total_activity), 2) as avg_total_activity,
        count(distinct billing_account_id) as accounts
    from (
        select * from pre_churn
        union all
        select * from pre_contraction
        union all
        select * from retained
    )
    group by 1, 2
    order by 1, 2
""").df().to_csv('outputs/q2_q3_retention_analysis.csv', index=False)
print("done: outputs/q2_q3_retention_analysis.csv")

# ==================================================================== #
# Q6: What should Product learn from usage and adoption patterns?
# ==================================================================== #
print("exporting Q6...")
conn.execute("""
    select
        customer_segment,
        snapshot_month,
        round(avg(active_user_rate), 2) as avg_active_user_rate,
        round(avg(total_meetings), 2) as avg_meetings,
        round(avg(total_ai_chats), 2) as avg_ai_chats,
        round(avg(days_with_meetings), 2) as avg_days_with_meetings,
        round(avg(days_with_notes_synced), 2) as avg_days_with_notes_synced,
        round(avg(days_with_tasks), 2) as avg_days_with_tasks,
        round(avg(days_with_dashboards), 2) as avg_days_with_dashboards,
        round(avg(total_activity), 2) as avg_total_activity,
        count(distinct billing_account_id) as accounts
    from mart_account_lifecycle_monthly
    where is_new_account = 0
    group by 1, 2
    order by 1, 2
""").df().to_csv('outputs/q6_product_insights.csv', index=False)
print("done: outputs/q6_product_insights.csv")

# ==================================================================== #
# Q7: What should Leadership monitor monthly?
# ==================================================================== #
print("exporting Q7...")
conn.execute("""
    with max_month as (
        select
            max(snapshot_month) as last_month,
            quarter(max(snapshot_month)) as last_quarter,
            year(max(snapshot_month)) as last_year,
            date_diff('month', date_trunc('year', max(snapshot_month)), max(snapshot_month)) + 1 as months_into_year,
            date_diff('month', date_trunc('quarter', max(snapshot_month)), max(snapshot_month)) + 1 as months_into_quarter
        from mart_account_lifecycle_monthly
    ),
    periods as (
        select
            m.billing_account_id,
            m.customer_segment,
            m.snapshot_month,
            m.ending_arr,
            m.arr_change,
            m.active_users,
            m.total_activity,
            m.total_meetings,
            m.lifecycle_segment,
            m.is_expansion_ready,
            case when m.snapshot_month = mx.last_month then 1 else 0 end as is_this_month,
            case when m.snapshot_month = mx.last_month - interval '1 month' then 1 else 0 end as is_last_month,
            case when year(m.snapshot_month) = mx.last_year
                and quarter(m.snapshot_month) = mx.last_quarter
                and date_diff('month', date_trunc('quarter', m.snapshot_month), m.snapshot_month) < mx.months_into_quarter
                then 1 else 0 end as is_this_quarter,
            case when year(m.snapshot_month) = mx.last_year
                and quarter(m.snapshot_month) = mx.last_quarter - 1
                and date_diff('month', date_trunc('quarter', m.snapshot_month), m.snapshot_month) < mx.months_into_quarter
                then 1 else 0 end as is_last_quarter,
            case when year(m.snapshot_month) = mx.last_year
                and date_diff('month', date_trunc('year', m.snapshot_month), m.snapshot_month) < mx.months_into_year
                then 1 else 0 end as is_this_year,
            case when year(m.snapshot_month) = mx.last_year - 1
                and date_diff('month', date_trunc('year', m.snapshot_month), m.snapshot_month) < mx.months_into_year
                then 1 else 0 end as is_last_year
        from mart_account_lifecycle_monthly m
        cross join max_month mx
    ),
    summary as (
        select
            period_name,
            customer_segment,
            count(distinct billing_account_id) as total_accounts,
            round(sum(ending_arr), 2) as ending_arr,
            round(sum(arr_change), 2) as arr_change,
            round(avg(active_users), 2) as avg_active_users,
            round(sum(total_activity), 2) as total_activity,
            round(sum(total_meetings), 2) as total_meetings,
            count(distinct case when lifecycle_segment = 'healthy' then billing_account_id end) as healthy,
            count(distinct case when lifecycle_segment = 'at_risk' then billing_account_id end) as at_risk,
            count(distinct case when lifecycle_segment = 'under_adopted' then billing_account_id end) as under_adopted,
            count(distinct case when is_expansion_ready = 1 then billing_account_id end) as expansion_ready
        from (
            select 'this_month' as period_name, * from periods where is_this_month = 1
            union all
            select 'last_month' as period_name, * from periods where is_last_month = 1
            union all
            select 'this_quarter' as period_name, * from periods where is_this_quarter = 1
            union all
            select 'last_quarter' as period_name, * from periods where is_last_quarter = 1
            union all
            select 'this_year' as period_name, * from periods where is_this_year = 1
            union all
            select 'last_year' as period_name, * from periods where is_last_year = 1
        )
        group by 1, 2
        union all
        select
            period_name,
            'overall' as customer_segment,
            count(distinct billing_account_id) as total_accounts,
            round(sum(ending_arr), 2) as ending_arr,
            round(sum(arr_change), 2) as arr_change,
            round(avg(active_users), 2) as avg_active_users,
            round(sum(total_activity), 2) as total_activity,
            round(sum(total_meetings), 2) as total_meetings,
            count(distinct case when lifecycle_segment = 'healthy' then billing_account_id end) as healthy,
            count(distinct case when lifecycle_segment = 'at_risk' then billing_account_id end) as at_risk,
            count(distinct case when lifecycle_segment = 'under_adopted' then billing_account_id end) as under_adopted,
            count(distinct case when is_expansion_ready = 1 then billing_account_id end) as expansion_ready
        from (
            select 'this_month' as period_name, * from periods where is_this_month = 1
            union all
            select 'last_month' as period_name, * from periods where is_last_month = 1
            union all
            select 'this_quarter' as period_name, * from periods where is_this_quarter = 1
            union all
            select 'last_quarter' as period_name, * from periods where is_last_quarter = 1
            union all
            select 'this_year' as period_name, * from periods where is_this_year = 1
            union all
            select 'last_year' as period_name, * from periods where is_last_year = 1
        )
        group by 1
    )
    select *
    from summary
    order by customer_segment, period_name
""").df().to_csv('outputs/q7_leadership_summary.csv', index=False)
print("done: outputs/q7_leadership_summary.csv")

print("\nall exports complete.")