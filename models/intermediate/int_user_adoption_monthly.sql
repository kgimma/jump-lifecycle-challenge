-- Grain: one row per app_account_id per snapshot_month.
-- User adoption signals
select
    au.app_account_id,
    date_trunc('month', ud.date) as snapshot_month,

    count(distinct au.app_user_id) as total_users,
    count(distinct case when ud.total_activity > 0 then au.app_user_id end) as active_users,
    count(distinct case when au.is_account_owner = true then au.app_user_id end) as owner_count,
    round(
        count(distinct case when ud.total_activity > 0 then au.app_user_id end) * 1.0 / nullif(count(distinct au.app_user_id), 0), 2) as active_user_rate,
    max(case when ud.total_activity > 0 then 1 else 0 end) as has_any_activity,

    -- days with activity per feature
    sum(case when ud.meeting_count > 0 then 1 else 0 end) as days_with_meetings,
    sum(case when ud.ai_chat_message_submitted_count > 0 then 1 else 0 end) as days_with_ai_chat,
    sum(case when ud.page_view_count > 0 then 1 else 0 end) as days_with_page_views,
    sum(case when ud.page_visit_count > 0 then 1 else 0 end) as days_with_page_visits,
    sum(case when ud.note_viewed_count > 0 then 1 else 0 end) as days_with_notes_viewed,
    sum(case when ud.note_synced_count > 0 then 1 else 0 end) as days_with_notes_synced,
    sum(case when ud.dashboard_viewed_count > 0 then 1 else 0 end) as days_with_dashboards,
    sum(case when ud.meeting_agenda_viewed_count > 0 then 1 else 0 end) as days_with_meeting_agendas,
    sum(case when ud.task_synced_count > 0 then 1 else 0 end) as days_with_tasks

from stg_app_users au
left join (
    select
        app_user_id,
        date,
        meeting_count,
        ai_chat_message_submitted_count,
        page_view_count,
        page_visit_count,
        note_viewed_count,
        note_synced_count,
        dashboard_viewed_count,
        meeting_agenda_viewed_count,
        task_synced_count,
        meeting_count + page_view_count + page_visit_count
            + note_viewed_count + ai_chat_message_submitted_count
            + note_synced_count + dashboard_viewed_count
            + meeting_agenda_viewed_count + task_synced_count as total_activity
    from stg_usage_daily
) ud on au.app_user_id = ud.app_user_id

where 1=1
    and au.is_internal_user = false
    and au.app_account_id is not null

group by 1, 2


-- Notes:
-- - A quick look at the active/inactive clients by user utilization (explore.py)
--     - The top buckets were either 100% or 0% of users using it for a client
-- - Prelim co-adaption exploration (explore.py)
--     - Meetings were used more than ai chat. When any combination of these is used it's a pretty high adoption rate anyway client-wide
