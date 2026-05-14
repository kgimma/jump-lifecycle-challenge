# NOTE: AI helped me make this page. I would ordinarily send this to the warehouse like big query
# NOTE: It's kind of hard to read the outputs in the terminal. I was copying and pasting them into either an excel page or copying and pasting into Claude to make the table a little easier to read. 
#       Claude was particularly helpful in seeing the tables that are sectioned off by things like business segment
#       On the job you wouldn't have to do this because you could just run it right in BQ and/or use a visualization tool for the last step

#That would change the paths in FROM to {{ ref ('table_name') }}
#It would then go through dbt to BQ with dbt run and we'd schedule however you're already scheduling everything else

# Since I don't have that for the challenge, AI helped me make this and I'll have the outputs at the bottom. 

import duckdb
import re

conn = duckdb.connect()

def register_view(folder, name):
    sql = open(f'models/{folder}/{name}.sql').read()
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    conn.execute(f'create or replace view {name} as ({sql})')
    print(f'registered: {name}')


# ========== Shows all available staging, intermediate, and mart tables =========#
# staging
for name in ['stg_billing_accounts','stg_app_accounts','stg_app_users','stg_usage_daily','stg_arr_daily']:
    register_view('staging', name)

# intermediate
for name in ['int_account_bridge','int_arr_monthly','int_usage_monthly','int_user_adoption_monthly']:
    register_view('intermediate', name)

# marts
for name in ['mart_account_lifecycle_monthly']:
    register_view('marts', name)

# outputs

# ==================================================================== #
# ==================================================================== #
#              ||| Account Lifecycle Monthly Mart |||| 
# ==================================================================== #
# ==================================================================== #
# NOTE: I would suggest copying and pasting the results into a csv to see better. The terminal just doesn't build the table in a way I find particularly readable. 
#       I didn't want to download a bunch of CSVs that you might not want on your computer 



# ==================================================================== #
# Q1: Which accounts appear healthy, under-adopted, at risk, or expansion-ready?
# Q4: Which accounts appear expansion-ready?
# Q5: Which accounts should Customer Success or GTM prioritize, and why?
# ==================================================================== #


# Q1: Which accounts appear healthy, under-adopted, at risk, or expansion-ready?
#     - lifecycle_segment column
# Q4: Which accounts appear expansion-ready?
#     - is_expansion_ready flag
# Q5: Which accounts should Customer Success or GTM prioritize, and why?
#     - recommended_action column

#================== Part 1: Uncomment here, run, then comment out again! =======================#
# This shows what the possible ouputs are for 
    # lifecycle segment
    # is expansion ready
    # recommended action 
    # reason code 

# print("\n--- lifecycle_segment ---")
# print(conn.execute("select distinct lifecycle_segment from mart_account_lifecycle_monthly order by 1").df().to_string())

# print("\n--- is_expansion_ready ---")
# print(conn.execute("select distinct is_expansion_ready from mart_account_lifecycle_monthly order by 1").df().to_string())

# print("\n--- recommended_action ---")
# print(conn.execute("select distinct recommended_action from mart_account_lifecycle_monthly order by 1").df().to_string())

# print("\n--- reason_code ---")
# print(conn.execute("select distinct reason_code from mart_account_lifecycle_monthly order by 1").df().to_string())

#================== Part 2: Uncomment here, run, then comment out again! =======================#
# These are the monthly counts of lifecycle segment + recommended action breakdowns. This is good for executive dashboard or seeing trends over time

# result = conn.execute("""
#     select 
#         snapshot_month,
#         lifecycle_segment,
#         recommended_action,
#         count(distinct billing_account_id) as accounts
#     from mart_account_lifecycle_monthly
#     group by 1, 2, 3
#     order by 1, 2, 3
# """).df()
# print(result.to_string())

#================== Part 3: Uncomment here, run, then comment out again! =======================#
# These are the monthly tags per billing account. This lets the CX and GTM teams see exactly which accounts to be looking at 

# print("\n--- Q1, Q4, Q5: Account Lifecycle Signals by Month ---")
# print(conn.execute("""
#     select
#         snapshot_month,
#         billing_account_id,
#         billing_account_name,
#         customer_segment,
#         lifecycle_segment,
#         is_expansion_ready,
#         recommended_action,
#         reason_code
#     from mart_account_lifecycle_monthly
#     order by snapshot_month, billing_account_id
# """).df().to_string())



# ==================================================================== #
# Q2: Which product adoption patterns appear associated with retention?
# Q3: Which product adoption patterns appear before churn or contraction?
# Q6: What should Product learn from usage and adoption patterns?
# ==================================================================== #

# Q2: Which product adoption patterns appear associated with retention?
# Q3: Which product adoption patterns appear before churn or contraction?
# NOTE: I decided to split into 4 groups active retained, inactive retained, contracted, and churned 
#Churned = FIRST month ARR hits zero, then looks at 3 months prir to get monthly avg
#Retained active = never churned, some activity in last 3 months
#Retained inactive = never churned, no activity last 3 months
#Contracted = ARR decreased, but not zero 

#Q6: What should Product learn from usage and adoption patterns? -- NOTE this doesn't have it's own pull, but really what we've learned from these two queries
#The active user rate seems to be the bigger indicator of churn based on this. The people who are using it tend to use it as much or more as the users in active accounts
#Large segmente is an outlier here. Even with an impressively high active user rate, they churned. My next question would maybe be pricing? Or growing competition?
#Contracted accounts show definitive decreases in the active user rate. 
# Small, Medium, and Large accounts showed different contraction and churn patterns, so each should be considered separately 
# Almost a quarter of all retained accounts are inactive. Product should find out why

# print(conn.execute("""
#     with churned_accounts as (
#         select billing_account_id, min(snapshot_month) as churn_month
#         from mart_account_lifecycle_monthly
#         where arr_movement_type = 'churned'
#         group by 1
#     ),
#     contracted_accounts as (
#         select billing_account_id, min(snapshot_month) as contraction_month
#         from mart_account_lifecycle_monthly
#         where arr_movement_type = 'contraction'
#           and billing_account_id not in (select billing_account_id from churned_accounts)
#         group by 1
#     ),
#     retained_activity as (
#         select
#             billing_account_id,
#             sum(total_activity) as total_activity_last_3_months
#         from mart_account_lifecycle_monthly
#         where billing_account_id not in (select billing_account_id from churned_accounts)
#           and billing_account_id not in (select billing_account_id from contracted_accounts)
#           and is_new_account = 0
#           and snapshot_month >= date_trunc('month', current_date) - interval '3 months'
#         group by 1
#     ),
#     pre_churn as (
#         select
#             m.billing_account_id,
#             m.customer_segment,
#             'churned' as retention_status,
#             m.active_user_rate,
#             m.total_meetings,
#             m.total_ai_chats,
#             m.days_with_meetings,
#             m.days_with_dashboards,
#             m.days_with_notes_synced,
#             m.days_with_tasks,
#             m.total_activity
#         from mart_account_lifecycle_monthly m
#         join churned_accounts c on m.billing_account_id = c.billing_account_id
#         where m.snapshot_month < c.churn_month
#           and m.snapshot_month >= c.churn_month - interval '3 months'
#           and m.is_new_account = 0
#     ),
#     pre_contraction as (
#         select
#             m.billing_account_id,
#             m.customer_segment,
#             'contracted' as retention_status,
#             m.active_user_rate,
#             m.total_meetings,
#             m.total_ai_chats,
#             m.days_with_meetings,
#             m.days_with_dashboards,
#             m.days_with_notes_synced,
#             m.days_with_tasks,
#             m.total_activity
#         from mart_account_lifecycle_monthly m
#         join contracted_accounts c on m.billing_account_id = c.billing_account_id
#         where m.snapshot_month < c.contraction_month
#           and m.snapshot_month >= c.contraction_month - interval '3 months'
#           and m.is_new_account = 0
#     ),
#     retained as (
#         select
#             m.billing_account_id,
#             m.customer_segment,
#             case when ra.total_activity_last_3_months = 0
#                 then 'retained_inactive'
#                 else 'retained_active'
#             end as retention_status,
#             m.active_user_rate,
#             m.total_meetings,
#             m.total_ai_chats,
#             m.days_with_meetings,
#             m.days_with_dashboards,
#             m.days_with_notes_synced,
#             m.days_with_tasks,
#             m.total_activity
#         from mart_account_lifecycle_monthly m
#         join retained_activity ra on m.billing_account_id = ra.billing_account_id
#         where m.is_new_account = 0
#           and m.snapshot_month >= date_trunc('month', current_date) - interval '3 months'
#     )
#     select
#         customer_segment,
#         retention_status,
#         round(avg(active_user_rate), 2) as avg_active_user_rate,
#         round(avg(total_meetings), 2) as avg_meetings,
#         round(avg(total_ai_chats), 2) as avg_ai_chats,
#         round(avg(days_with_meetings), 2) as avg_days_with_meetings,
#         round(avg(days_with_notes_synced), 2) as avg_days_with_notes_synced,
#         round(avg(days_with_tasks), 2) as avg_days_with_tasks,
#         round(avg(total_activity), 2) as avg_total_activity,
#         count(distinct billing_account_id) as accounts
#     from (
#         select * from pre_churn
#         union all
#         select * from pre_contraction
#         union all
#         select * from retained
#     )
#     group by 1, 2
#     order by 1, 2
# """).df().to_string())

# ==================================================================== #
# Q7: What should Leadership monitor monthly?
# ==================================================================== #

# Tracks account health, ARR movement, and engagement across segments
# Covers this month vs last month, this quarter vs last quarter, and this year vs last year -- all prorated to the same number of months
# It's month level and not day level to show the concept of the multi-use mart. 


# print(conn.execute("""
#     with max_month as (
#         select
#             max(snapshot_month) as last_month,
#             quarter(max(snapshot_month)) as last_quarter,
#             year(max(snapshot_month)) as last_year,
#             date_diff('month', date_trunc('year', max(snapshot_month)), max(snapshot_month)) + 1 as months_into_year,
#             date_diff('month', date_trunc('quarter', max(snapshot_month)), max(snapshot_month)) + 1 as months_into_quarter
#         from mart_account_lifecycle_monthly
#     ),
#     periods as (
#         select
#             m.billing_account_id,
#             m.customer_segment,
#             m.snapshot_month,
#             m.ending_arr,
#             m.arr_change,
#             m.active_users,
#             m.total_activity,
#             m.total_meetings,
#             m.lifecycle_segment,
#             m.is_expansion_ready,
#             -- this month
#             case when m.snapshot_month = mx.last_month then 1 else 0 end as is_this_month,
#             -- last month
#             case when m.snapshot_month = mx.last_month - interval '1 month' then 1 else 0 end as is_last_month,
#             -- this quarter
#             case when year(m.snapshot_month) = mx.last_year
#                 and quarter(m.snapshot_month) = mx.last_quarter
#                 and date_diff('month', date_trunc('quarter', m.snapshot_month), m.snapshot_month) < mx.months_into_quarter
#                 then 1 else 0 end as is_this_quarter,
#             -- last quarter
#             case when year(m.snapshot_month) = mx.last_year
#                 and quarter(m.snapshot_month) = mx.last_quarter - 1
#                 and date_diff('month', date_trunc('quarter', m.snapshot_month), m.snapshot_month) < mx.months_into_quarter
#                 then 1 else 0 end as is_last_quarter,
#             -- this year
#             case when year(m.snapshot_month) = mx.last_year
#                 and date_diff('month', date_trunc('year', m.snapshot_month), m.snapshot_month) < mx.months_into_year
#                 then 1 else 0 end as is_this_year,
#             -- last year
#             case when year(m.snapshot_month) = mx.last_year - 1
#                 and date_diff('month', date_trunc('year', m.snapshot_month), m.snapshot_month) < mx.months_into_year
#                 then 1 else 0 end as is_last_year
#         from mart_account_lifecycle_monthly m
#         cross join max_month mx
#     ),
#     summary as (
#         select
#             period_name,
#             customer_segment,
#             count(distinct billing_account_id) as total_accounts,
#             round(sum(ending_arr), 2) as ending_arr,
#             round(sum(arr_change), 2) as arr_change,
#             round(avg(active_users), 2) as avg_active_users,
#             round(sum(total_activity), 2) as total_activity,
#             round(sum(total_meetings), 2) as total_meetings,
#             count(distinct case when lifecycle_segment = 'healthy' then billing_account_id end) as healthy,
#             count(distinct case when lifecycle_segment = 'at_risk' then billing_account_id end) as at_risk,
#             count(distinct case when lifecycle_segment = 'under_adopted' then billing_account_id end) as under_adopted,
#             count(distinct case when is_expansion_ready = 1 then billing_account_id end) as expansion_ready
#         from (
#             select 'this_month' as period_name, * from periods where is_this_month = 1
#             union all
#             select 'last_month' as period_name, * from periods where is_last_month = 1
#             union all
#             select 'this_quarter' as period_name, * from periods where is_this_quarter = 1
#             union all
#             select 'last_quarter' as period_name, * from periods where is_last_quarter = 1
#             union all
#             select 'this_year' as period_name, * from periods where is_this_year = 1
#             union all
#             select 'last_year' as period_name, * from periods where is_last_year = 1
#         )
#         group by 1, 2
#         union all
#         select
#             period_name,
#             'overall' as customer_segment,
#             count(distinct billing_account_id) as total_accounts,
#             round(sum(ending_arr), 2) as ending_arr,
#             round(sum(arr_change), 2) as arr_change,
#             round(avg(active_users), 2) as avg_active_users,
#             round(sum(total_activity), 2) as total_activity,
#             round(sum(total_meetings), 2) as total_meetings,
#             count(distinct case when lifecycle_segment = 'healthy' then billing_account_id end) as healthy,
#             count(distinct case when lifecycle_segment = 'at_risk' then billing_account_id end) as at_risk,
#             count(distinct case when lifecycle_segment = 'under_adopted' then billing_account_id end) as under_adopted,
#             count(distinct case when is_expansion_ready = 1 then billing_account_id end) as expansion_ready
#         from (
#             select 'this_month' as period_name, * from periods where is_this_month = 1
#             union all
#             select 'last_month' as period_name, * from periods where is_last_month = 1
#             union all
#             select 'this_quarter' as period_name, * from periods where is_this_quarter = 1
#             union all
#             select 'last_quarter' as period_name, * from periods where is_last_quarter = 1
#             union all
#             select 'this_year' as period_name, * from periods where is_this_year = 1
#             union all
#             select 'last_year' as period_name, * from periods where is_last_year = 1
#         )
#         group by 1
#     )
#     select *
#     from summary
#     order by customer_segment, period_name
# """).df().to_string())


