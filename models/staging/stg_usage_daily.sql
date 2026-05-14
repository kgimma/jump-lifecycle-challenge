-- only days with at least one action
-- one row / user / day 

select
    date,
    app_user_id,
    meeting_count,
    page_view_count,
    page_visit_count,
    note_viewed_count,
    ai_chat_message_submitted_count,
    note_synced_count,
    dashboard_viewed_count,
    meeting_agenda_viewed_count,
    task_synced_count,
    meeting_count
    + page_view_count
    + page_visit_count
    + note_viewed_count
    + ai_chat_message_submitted_count
    + note_synced_count
    + dashboard_viewed_count
    + meeting_agenda_viewed_count
    + task_synced_count as total_activity

from 'data/app_usage_daily.csv'

where 1=1
    and app_user_id is not null
    and date is not null