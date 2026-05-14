-- Look below query for notes and definitions 

with

accounts as (
    select distinct
        ba.billing_account_id,
        ba.billing_account_name,
        ba.customer_segment,
        ba.created_date as billing_created_date,
        aa.app_account_id,
        aa.app_signup_date,
        aa.trial_end_date,
        date_trunc('month', arr.date) as snapshot_month
    from stg_billing_accounts ba
    left join int_account_bridge aa
        on ba.billing_account_id = aa.billing_account_id
    inner join stg_arr_daily arr
        on ba.billing_account_id = arr.billing_account_id
    where ba.billing_account_id is not null
),

arr_signals as (
    select
        a.billing_account_id,
        a.snapshot_month,
        a.starting_arr,
        a.ending_arr,
        a.arr_change,
        a.arr_movement_type,
        lag(a.ending_arr) over (partition by a.billing_account_id order by a.snapshot_month) as prev_month_arr
    from int_arr_monthly a
),

usage_signals as (
    select
        ab.billing_account_id,
        u.snapshot_month,
        sum(u.total_activity) as total_activity,
        sum(u.total_meetings) as total_meetings,
        sum(u.total_ai_chats) as total_ai_chats,
        sum(u.total_page_views) as total_page_views,
        sum(u.total_page_visits) as total_page_visits,
        sum(u.total_notes_viewed) as total_notes_viewed,
        sum(u.total_notes_synced) as total_notes_synced,
        sum(u.total_dashboards_viewed) as total_dashboards_viewed,
        sum(u.total_meeting_agendas_viewed) as total_meeting_agendas_viewed,
        sum(u.total_tasks_synced) as total_tasks_synced,
        sum(u.active_users) as active_users
    from int_usage_monthly u
    join int_account_bridge ab
        on u.app_account_id = ab.app_account_id
    group by 1, 2
),

adoption_signals as (
    select
        ab.billing_account_id,
        ua.snapshot_month,
        sum(ua.total_users) as total_users,
        sum(ua.active_users) as active_users,
        sum(ua.owner_count) as owner_count,
        avg(ua.active_user_rate) as active_user_rate,
        max(ua.has_any_activity) as has_any_activity,
        sum(ua.days_with_meetings) as days_with_meetings,
        sum(ua.days_with_ai_chat) as days_with_ai_chat,
        sum(ua.days_with_page_views) as days_with_page_views,
        sum(ua.days_with_page_visits) as days_with_page_visits,
        sum(ua.days_with_notes_viewed) as days_with_notes_viewed,
        sum(ua.days_with_notes_synced) as days_with_notes_synced,
        sum(ua.days_with_dashboards) as days_with_dashboards,
        sum(ua.days_with_meeting_agendas) as days_with_meeting_agendas,
        sum(ua.days_with_tasks) as days_with_tasks,
        lag(avg(ua.active_user_rate)) over (partition by ab.billing_account_id order by ua.snapshot_month) as prev_month_active_user_rate
    from int_user_adoption_monthly ua
    join int_account_bridge ab
        on ua.app_account_id = ab.app_account_id
    group by 1, 2
),

expansion_signals as (
    select
        billing_account_id,
        snapshot_month,
        max(case when arr_movement_type = 'expansion' then 1 else 0 end) as had_expansion,
        max(case when arr_movement_type = 'expansion'
            and snapshot_month >= date_trunc('month', current_date) - interval '3 months'
            then 1 else 0 end) as expanded_last_3_months
    from int_arr_monthly
    group by 1, 2
),

segment_scores as (
    select
        a.billing_account_id,
        a.billing_account_name,
        a.customer_segment,
        a.billing_created_date,
        a.app_account_id,
        a.app_signup_date,
        a.snapshot_month,
        coalesce(arr.starting_arr, 0) as starting_arr,
        coalesce(arr.ending_arr, 0) as ending_arr,
        coalesce(arr.arr_change, 0) as arr_change,
        arr.arr_movement_type,
        arr.prev_month_arr,
        coalesce(u.total_activity, 0) as total_activity,
        coalesce(u.total_meetings, 0) as total_meetings,
        coalesce(u.total_ai_chats, 0) as total_ai_chats,
        coalesce(u.total_page_views, 0) as total_page_views,
        coalesce(u.total_page_visits, 0) as total_page_visits,
        coalesce(u.total_notes_viewed, 0) as total_notes_viewed,
        coalesce(u.total_notes_synced, 0) as total_notes_synced,
        coalesce(u.total_dashboards_viewed, 0) as total_dashboards_viewed,
        coalesce(u.total_meeting_agendas_viewed, 0) as total_meeting_agendas_viewed,
        coalesce(u.total_tasks_synced, 0) as total_tasks_synced,
        coalesce(ad.total_users, 0) as total_users,
        coalesce(ad.active_users, 0) as active_users,
        coalesce(ad.owner_count, 0) as owner_count,
        coalesce(ad.active_user_rate, 0) as active_user_rate,
        ad.prev_month_active_user_rate,
        coalesce(ad.has_any_activity, 0) as has_any_activity,
        coalesce(ad.days_with_meetings, 0) as days_with_meetings,
        coalesce(ad.days_with_ai_chat, 0) as days_with_ai_chat,
        coalesce(ad.days_with_page_views, 0) as days_with_page_views,
        coalesce(ad.days_with_page_visits, 0) as days_with_page_visits,
        coalesce(ad.days_with_notes_viewed, 0) as days_with_notes_viewed,
        coalesce(ad.days_with_notes_synced, 0) as days_with_notes_synced,
        coalesce(ad.days_with_dashboards, 0) as days_with_dashboards,
        coalesce(ad.days_with_meeting_agendas, 0) as days_with_meeting_agendas,
        coalesce(ad.days_with_tasks, 0) as days_with_tasks,
        coalesce(ex.had_expansion, 0) as had_expansion,
        coalesce(ex.expanded_last_3_months, 0) as expanded_last_3_months,
        case when a.snapshot_month <= date_trunc('month', coalesce(a.app_signup_date, a.billing_created_date) + interval '30 days')
            then 1 else 0 end as is_new_account
    from accounts a
    left join arr_signals arr
        on a.billing_account_id = arr.billing_account_id
        and a.snapshot_month = arr.snapshot_month
    left join usage_signals u
        on a.billing_account_id = u.billing_account_id
        and a.snapshot_month = u.snapshot_month
    left join adoption_signals ad
        on a.billing_account_id = ad.billing_account_id
        and a.snapshot_month = ad.snapshot_month
    left join expansion_signals ex
        on a.billing_account_id = ex.billing_account_id
        and a.snapshot_month = ex.snapshot_month
),

final as (
    select
        *,
        case
            when is_new_account = 1 then 'new'
            when active_user_rate >= 0.80
                and arr_movement_type in ('stable', 'expansion')
                and (prev_month_active_user_rate is null
                    or active_user_rate >= prev_month_active_user_rate * 0.98)
                then 'healthy'
            when active_user_rate < 0.60
                or arr_movement_type = 'contraction'
                or (prev_month_active_user_rate is not null
                    and active_user_rate < prev_month_active_user_rate * 0.98)
                then 'at_risk'
            when active_user_rate >= 0.60
                then 'under_adopted'
            else 'unknown'
        end as lifecycle_segment,
        case
            when is_new_account = 0
                and expanded_last_3_months = 0
                and total_activity > 0
                and active_user_rate >= 0.80
                and total_meetings > 0
                then 1
            else 0
        end as is_expansion_ready,
        case
            when is_new_account = 1 then 'new_account'
            when arr_movement_type = 'churned' then 'churned'
            when arr_movement_type = 'contraction' then 'recent_contraction'
            when active_user_rate = 0 then 'zero_active_users'
            when active_user_rate < 0.60 then 'low_active_user_rate'
            when prev_month_active_user_rate is not null
                and active_user_rate < prev_month_active_user_rate * 0.98
                then 'usage_declining'
            when active_user_rate >= 0.80
                and arr_movement_type in ('stable', 'expansion')
                then 'healthy_usage_and_arr'
            when expanded_last_3_months = 1 then 'recently_expanded'
            else 'stable_moderate_usage'
        end as reason_code,
        case
            when is_new_account = 1 then 'monitor_activation'
            when arr_movement_type = 'churned' then 'churn_review'
            when arr_movement_type = 'contraction' then 'cs_outreach_contraction'
            when active_user_rate = 0 then 'cs_outreach_no_usage'
            when active_user_rate < 0.60 then 'cs_outreach_low_adoption'
            when prev_month_active_user_rate is not null
                and active_user_rate < prev_month_active_user_rate * 0.98
                then 'cs_outreach_declining'
            when is_expansion_ready = 1 then 'gtm_expansion_outreach'
            when active_user_rate >= 0.80
                and arr_movement_type in ('stable', 'expansion')
                then 'nurture'
            else 'monitor'
        end as recommended_action
    from segment_scores
)

select * from final



/*

Segment definitions
NOTE: Think of these as starting examples. 
Sometimes when I don't know the full answer I want to get something out there to start to play with and manipulate

Healthy
- active_user_rate >= 80% AND
- ARR stable or growing AND
- <2% MoM decline in active users

Under-adopted
- active_user_rate 60-79%
- Not flagged as at-risk

At-risk
- active_user_rate < 60% OR
- MoM decline in active users OR
- Recent contraction in ARR

Expansion-ready (independent of health segment)
- High usage intensity among active users
- No expansion event in the last 3 months
- Segment/size not a factor for now
- NOTE: worth considering in future whether Small->Medium differs from Medium->Large

New accounts
- Exclude first 30 days from all segments
- NOTE: 30 days may span 2 calendar months -- up for discussion, could simplify to first 1-2 calendar months

Implementation notes
- Cascading CASE statement (healthy checked first, at-risk last)
- Use CTE with weighted factors so we can tune later
*/