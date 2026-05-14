select
    app_account_id,
    app_account_name,
    app_parent_account_id,
    app_root_account_id,
    billing_account_bridge_id,
    signup_date,
    trial_end_date,
    is_internal_account

from 'data/app_accounts.csv'

where 1=1
    and app_account_id is not null
    and is_internal_account = false
