select
    app_user_id,
    app_user_name,
    app_account_id,
    seat_tiers_array,
    signup_date,
    is_account_owner,
    is_internal_user

from 'data/app_users.csv'

where 1=1
    and app_user_id is not null
    and is_internal_user = false