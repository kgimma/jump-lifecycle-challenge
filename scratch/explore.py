import duckdb
import re
conn = duckdb.connect()

#===============================STAGING===================#

# Making sure there's only one row per billing account name 
# print(conn.execute("""
#     SELECT 
#                    distinct billing_account_bridge_id,
#                    count(billing_account_name)
#     FROM 'data/billing_accounts.csv'
#                    group by 1
#                    order by 2 desc
# """).df())



# How many accounts?
# print(conn.execute("""
#     SELECT 
#                    count(distinct billing_account_name)
                   
#     FROM 'data/billing_accounts.csv'
                   
# """).df())

#========================INTERMEDIATE=====================#

# import duckdb

# conn = duckdb.connect()

# sql = open('models/intermediate/int_account_bridge.sql').read()
# result = conn.execute(sql).df()
# print(f"int_account_bridge: {len(result)} rows")
# print(result.head())

#Which billing accounts have more than one app account?
# dupes = conn.execute("""
#     SELECT 
#         billing_account_id,
#         COUNT(app_account_id) as app_account_count
#     FROM (
#         SELECT * FROM 'data/billing_accounts.csv' ba
#         LEFT JOIN 'data/app_accounts.csv' aa
#             ON ba.billing_account_bridge_id = aa.billing_account_bridge_id
#             AND aa.is_internal_account = false
#         WHERE ba.billing_account_id IS NOT NULL
#     )
#     GROUP BY billing_account_id
#     HAVING COUNT(app_account_id) > 1
#     ORDER BY 2 DESC
# """).df()
# print(dupes)

# check = conn.execute("""
#     SELECT 
#         COUNT(*) as total_rows,
#         COUNT(DISTINCT billing_account_id) as unique_billing_accounts,
#         COUNT(DISTINCT app_account_id) as unique_app_accounts,
#         COUNT(DISTINCT billing_account_id || '-' || COALESCE(app_account_id, 'none')) as unique_combinations
#     FROM (
#         SELECT ba.billing_account_id, aa.app_account_id
#         FROM 'data/billing_accounts.csv' ba
#         LEFT JOIN 'data/app_accounts.csv' aa
#             ON ba.billing_account_bridge_id = aa.billing_account_bridge_id
#             AND aa.is_internal_account = false
#         WHERE ba.billing_account_id IS NOT NULL
#     )
# """).df()
# print(check)

#    total_rows  unique_billing_accounts  unique_app_accounts  unique_combinations
# 0       22537                    22000                 5278                22537


# Did anyone have more than one movement type in the same month? 
# multi_movement = conn.execute("""
#     WITH monthly AS (
#         SELECT
#             billing_account_id,
#             date_trunc('month', date) as snapshot_month,
#             min(starting_arr) as starting_arr,
#             max(ending_arr) as ending_arr
#         FROM 'data/arr_daily.csv'
#         WHERE billing_account_id IS NOT NULL
#         GROUP BY 1, 2
#     ),
#     movements AS (
#         SELECT
#             billing_account_id,
#             snapshot_month,
#             starting_arr,
#             ending_arr,
#             CASE
#                 WHEN ending_arr = 0 AND starting_arr > 0 THEN 'churned'
#                 WHEN ending_arr > starting_arr THEN 'expansion'
#                 WHEN ending_arr < starting_arr THEN 'contraction'
#                 WHEN ending_arr = starting_arr THEN 'stable'
#                 ELSE 'unknown'
#             END as arr_movement_type
#         FROM monthly
#     )
#     SELECT
#         billing_account_id,
#         COUNT(DISTINCT arr_movement_type) as distinct_movement_types,
#         STRING_AGG(DISTINCT arr_movement_type, ', ') as movement_types
#     FROM movements
#     WHERE arr_movement_type != 'stable'
#     GROUP BY 1
#     HAVING COUNT(DISTINCT arr_movement_type) > 1
#     ORDER BY 2 DESC
#     LIMIT 20
# """).df()
# print(multi_movement)

# Empty DataFrame
# Columns: [billing_account_id, distinct_movement_types, movement_types]
# Index: []

# Monthly breakdown of movement

#print(conn.execute(open('models/intermediate/int_arr_monthly.sql').read()).df()['arr_movement_type'].value_counts().to_string())
# arr_monthly = conn.execute(open('models/intermediate/int_arr_monthly.sql').read()).df()
# pivot = arr_monthly.groupby(['snapshot_month', 'arr_movement_type'])['billing_account_id'].nunique().unstack(fill_value=0)
# print(pivot.to_string())

# print(conn.execute("""
#     SELECT
#         snapshot_month,
#         COUNT(CASE WHEN arr_movement_type = 'churned' THEN 1 END) as churned,
#         COUNT(CASE WHEN arr_movement_type = 'expansion' THEN 1 END) as expansion,
#         COUNT(CASE WHEN arr_movement_type = 'contraction' THEN 1 END) as contraction,
#         COUNT(CASE WHEN arr_movement_type = 'stable' THEN 1 END) as stable
#     FROM (
#         SELECT * FROM read_csv('data/arr_daily.csv')
#     ) raw
#     JOIN (
#         """ + open('models/intermediate/int_arr_monthly.sql').read() + """
#     ) monthly USING (billing_account_id)
#     GROUP BY 1
#     ORDER BY 1
# """).df().to_string())



# print(conn.execute("""
#     SELECT 
#         MIN(ending_arr) as min_ending_arr,
#         MAX(ending_arr) as max_ending_arr,
#         COUNT(DISTINCT CASE WHEN ending_arr = 0 THEN billing_account_id END) as accounts_with_zero_arr,
#         COUNT(DISTINCT billing_account_id) as total_accounts
#     FROM 'data/arr_daily.csv'
# """).df().to_string())

# print(conn.execute("""
#     SELECT *
#     FROM 'data/arr_daily.csv'
#     WHERE ending_arr = 0
#     LIMIT 10
# """).df().to_string())


# Which app accounts had zero usage ever?
# zero_usage = conn.execute("""
#     WITH user_activity AS (
#         SELECT 
#             au.app_account_id,
#             SUM(ud.meeting_count + ud.page_view_count + ud.page_visit_count 
#                 + ud.note_viewed_count + ud.ai_chat_message_submitted_count
#                 + ud.note_synced_count + ud.dashboard_viewed_count
#                 + ud.meeting_agenda_viewed_count + ud.task_synced_count) as total_activity
#         FROM 'data/app_users.csv' au
#         LEFT JOIN 'data/app_usage_daily.csv' ud
#             ON au.app_user_id = ud.app_user_id
#         WHERE au.is_internal_user = false
#         GROUP BY 1
#     )
#     SELECT 
#         aa.app_account_id,
#         aa.app_account_name,
#         aa.signup_date
#     FROM 'data/app_accounts.csv' aa
#     LEFT JOIN user_activity ua ON aa.app_account_id = ua.app_account_id
#     WHERE aa.is_internal_account = false
#       AND (ua.total_activity IS NULL OR ua.total_activity = 0)
#     ORDER BY aa.signup_date
# """).df()
# print(f"accounts with zero usage: {len(zero_usage)}")
# print(zero_usage.head(10))

# 1014 accounts, just under 20%

# What's the date distribution of this? -- AI gave me this question. I liked it so I followed the path
# print(conn.execute("""
#     WITH user_activity AS (
#         SELECT 
#             au.app_account_id,
#             SUM(ud.meeting_count + ud.page_view_count + ud.page_visit_count 
#                 + ud.note_viewed_count + ud.ai_chat_message_submitted_count
#                 + ud.note_synced_count + ud.dashboard_viewed_count
#                 + ud.meeting_agenda_viewed_count + ud.task_synced_count) as total_activity
#         FROM 'data/app_users.csv' au
#         LEFT JOIN 'data/app_usage_daily.csv' ud
#             ON au.app_user_id = ud.app_user_id
#         WHERE au.is_internal_user = false
#         GROUP BY 1
#     )
#     SELECT 
#         date_trunc('month', aa.signup_date) as signup_month,
#         COUNT(*) as zero_usage_accounts
#     FROM 'data/app_accounts.csv' aa
#     LEFT JOIN user_activity ua ON aa.app_account_id = ua.app_account_id
#     WHERE aa.is_internal_account = false
#       AND (ua.total_activity IS NULL OR ua.total_activity = 0)
#     GROUP BY 1
#     ORDER BY 1
# """).df().to_string())

# A quick look at the active/inactive clients by user utilization

# print(conn.execute("""
#     WITH adoption AS (
#         SELECT
#             au.app_account_id,
#             date_trunc('month', ud.date) as snapshot_month,
#             count(distinct au.app_user_id) as total_users,
#             count(distinct case when (
#                 ud.meeting_count + ud.page_view_count + ud.page_visit_count
#                 + ud.note_viewed_count + ud.ai_chat_message_submitted_count
#                 + ud.note_synced_count + ud.dashboard_viewed_count
#                 + ud.meeting_agenda_viewed_count + ud.task_synced_count) > 0
#                 then au.app_user_id end) as active_users
#         FROM 'data/app_users.csv' au
#         LEFT JOIN 'data/app_usage_daily.csv' ud ON au.app_user_id = ud.app_user_id
#         WHERE au.is_internal_user = false
#         GROUP BY 1, 2
#     )
#     SELECT
#         CASE
#             WHEN active_users = 0 THEN '0% active'
#             WHEN active_users * 1.0 / total_users < 0.25 THEN '1-24% active'
#             WHEN active_users * 1.0 / total_users < 0.50 THEN '25-49% active'
#             WHEN active_users * 1.0 / total_users < 0.75 THEN '50-74% active'
#             WHEN active_users * 1.0 / total_users < 1.00 THEN '75-99% active'
#             ELSE '100% active'
#         END as active_user_bucket,
#         COUNT(*) as account_months
#     FROM adoption
#     WHERE snapshot_month IS NOT NULL
#     GROUP BY 1
#     ORDER BY 2 DESC
# """).df().to_string())

# Prelim co-adaption exploration
# print(conn.execute("""
#     SELECT
#         CASE WHEN days_with_meetings > 0 THEN 'uses meetings' ELSE 'no meetings' END as meeting_usage,
#         CASE WHEN days_with_ai_chat > 0 THEN 'uses ai chat' ELSE 'no ai chat' END as ai_chat_usage,
#         COUNT(*) as account_months,
#         ROUND(AVG(active_user_rate), 2) as avg_active_user_rate
#     FROM (
#         SELECT
#             au.app_account_id,
#             date_trunc('month', ud.date) as snapshot_month,
#             count(distinct case when (
#                 ud.meeting_count + ud.page_view_count + ud.page_visit_count
#                 + ud.note_viewed_count + ud.ai_chat_message_submitted_count
#                 + ud.note_synced_count + ud.dashboard_viewed_count
#                 + ud.meeting_agenda_viewed_count + ud.task_synced_count) > 0
#                 then au.app_user_id end) * 1.0
#             / nullif(count(distinct au.app_user_id), 0) as active_user_rate,
#             SUM(ud.meeting_count) as days_with_meetings,
#             SUM(ud.ai_chat_message_submitted_count) as days_with_ai_chat
#         FROM 'data/app_users.csv' au
#         LEFT JOIN 'data/app_usage_daily.csv' ud ON au.app_user_id = ud.app_user_id
#         WHERE au.is_internal_user = false
#         GROUP BY 1, 2
#     )
#     WHERE snapshot_month IS NOT NULL
#     GROUP BY 1, 2
#     ORDER BY 3 DESC
# """).df().to_string())



# ===================== MARTS ====================#

# Adoption 1-100% a quick look to determine buckets

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

# print(conn.execute("""
#     WITH adoption AS (
#         SELECT
#             au.app_account_id,
#             date_trunc('month', ud.date) as snapshot_month,
#             COUNT(DISTINCT au.app_user_id) as total_users,
#             COUNT(DISTINCT CASE WHEN (
#                 ud.meeting_count + ud.page_view_count + ud.page_visit_count
#                 + ud.note_viewed_count + ud.ai_chat_message_submitted_count
#                 + ud.note_synced_count + ud.dashboard_viewed_count
#                 + ud.meeting_agenda_viewed_count + ud.task_synced_count) > 0
#                 THEN au.app_user_id END) as active_users
#         FROM 'data/app_users.csv' au
#         LEFT JOIN 'data/app_usage_daily.csv' ud ON au.app_user_id = ud.app_user_id
#         WHERE au.is_internal_user = false
#         GROUP BY 1, 2
#     ),
#     bucketed AS (
#         SELECT
#             CASE
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) = 0     THEN '0%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.10 THEN '1-10%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.20 THEN '11-20%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.30 THEN '21-30%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.40 THEN '31-40%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.50 THEN '41-50%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.60 THEN '51-60%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.70 THEN '61-70%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.80 THEN '71-80%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) <= 0.90 THEN '81-90%'
#                 WHEN active_users * 1.0 / NULLIF(total_users, 0) < 1.00  THEN '91-99%'
#                 ELSE '100%'
#             END as active_user_bucket,
#             COUNT(*) as account_months
#         FROM adoption
#         WHERE snapshot_month IS NOT NULL
#         GROUP BY 1
#     )
#     SELECT
#         active_user_bucket,
#         account_months,
#         ROUND(account_months * 100.0 / SUM(account_months) OVER (), 1) as pct_of_total
#     FROM bucketed
#     ORDER BY active_user_bucket
# """).df().to_string())

# Billing accounts with more than one churn event 
# print(conn.execute("""
#     select
#         billing_account_id,
#         count(distinct snapshot_month) as churn_months,
#         min(snapshot_month) as first_churn_month,
#         max(snapshot_month) as last_churn_month
#     from mart_account_lifecycle_monthly
#     where arr_movement_type = 'churned'
#     group by 1
#     having count(distinct snapshot_month) > 1
#     order by 2 desc
#     limit 20
# """).df().to_string())

# Validation 2: Are there usage records after ARR hits zero? --> yes! What's happening?
# print(conn.execute("""
#     select
#         billing_account_id,
#         snapshot_month,
#         ending_arr,
#         total_activity,
#         active_user_rate,
#         arr_movement_type
#     from mart_account_lifecycle_monthly
#     where ending_arr = 0
#       and total_activity > 0
#     order by billing_account_id, snapshot_month
#     limit 20
# """).df().to_string())

# How many retained accounts have zero usage in the last 3 months? -- Gahhh almost a quarter! Splitting final into 3 buckets
# Active retained, inactive retained, churned
# print(conn.execute("""
#     with churned_accounts as (
#         select billing_account_id
#         from mart_account_lifecycle_monthly
#         where arr_movement_type = 'churned'
#         group by 1
#     ),
#     retained_last_3 as (
#         select
#             billing_account_id,
#             sum(total_activity) as total_activity_last_3_months
#         from mart_account_lifecycle_monthly
#         where billing_account_id not in (select billing_account_id from churned_accounts)
#           and is_new_account = 0
#           and snapshot_month >= date_trunc('month', current_date) - interval '3 months'
#         group by 1
#     )
#     select
#         case when total_activity_last_3_months = 0 then 'zero activity' else 'has activity' end as activity_status,
#         count(distinct billing_account_id) as accounts,
#         round(count(distinct billing_account_id) * 100.0 / sum(count(distinct billing_account_id)) over (), 1) as pct_of_total
#     from retained_last_3
#     group by 1
#     order by 1
# """).df().to_string())

# Validation 3b: Q2 rerun with retained split into active vs inactive
print(conn.execute("""
    with churned_accounts as (
        select billing_account_id, min(snapshot_month) as churn_month
        from mart_account_lifecycle_monthly
        where arr_movement_type = 'churned'
        group by 1
    ),
    retained_activity as (
        select
            billing_account_id,
            sum(total_activity) as total_activity_last_3_months
        from mart_account_lifecycle_monthly
        where billing_account_id not in (select billing_account_id from churned_accounts)
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
        select * from retained
    )
    group by 1, 2
    order by 1, 2
""").df().to_string())