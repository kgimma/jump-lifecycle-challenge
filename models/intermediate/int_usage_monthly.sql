-- Grain: one row per app_account_id per snapshot_month.
-- Aggs daily usage events --> monthly totals.

select
    au.app_account_id,
    date_trunc('month', ud.date) as snapshot_month,
    count(distinct ud.app_user_id) as active_users,
    
    -- key metrics
    sum(ud.meeting_count) as total_meetings,
    sum(ud.page_view_count) as total_page_views,
    sum(ud.page_visit_count) as total_page_visits,
    sum(ud.note_viewed_count) as total_notes_viewed,
    sum(ud.ai_chat_message_submitted_count) as total_ai_chats,
    sum(ud.note_synced_count) as total_notes_synced,
    sum(ud.dashboard_viewed_count) as total_dashboards_viewed,
    sum(ud.meeting_agenda_viewed_count) as total_meeting_agendas_viewed,
    sum(ud.task_synced_count) as total_tasks_synced,

    -- total activity across ALL event types
    sum(
        ud.meeting_count
        + ud.page_view_count
        + ud.page_visit_count
        + ud.note_viewed_count
        + ud.ai_chat_message_submitted_count
        + ud.note_synced_count
        + ud.dashboard_viewed_count
        + ud.meeting_agenda_viewed_count
        + ud.task_synced_count
    ) as total_activity

from stg_usage_daily ud
left join stg_app_users au
    on ud.app_user_id = au.app_user_id

where 1=1
    and ud.app_user_id is not null
    and ud.date is not null

group by 1, 2


/*
Notes:
- Which app accounts had zero usage ever? (search in explore.py)
    - there was almost 20% which was higher than expected, so AI helped me find the next question
- What's the date distribution of this? -- AI gave me this question. I liked it so I followed the path (search in explore.py)
    - seems to steadily grow over time. makes sense bc the business is gowing. big jump for last month.
*/
