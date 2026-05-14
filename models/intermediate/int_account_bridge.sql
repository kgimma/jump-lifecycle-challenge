-- Maps billing accounts to app accounts --> bridge key.
-- Grain: one row per billing_account_id + app_account_id combination.

select
    ba.billing_account_id,
    ba.billing_account_name,
    ba.customer_segment,
    ba.created_date as billing_created_date,
    aa.app_account_id,
    aa.app_account_name,
    aa.app_root_account_id,
    aa.signup_date as app_signup_date,
    aa.trial_end_date,
    ba.billing_account_bridge_id

from stg_billing_accounts ba
left join stg_app_accounts aa
    on ba.billing_account_bridge_id = aa.billing_account_bridge_id
    and aa.is_internal_account = false

where 1=1
    and ba.billing_account_id is not null

/* 
Notes:

I saw there were more rows here than the number of billing accounts. I saw a note that this would be the case, but in explore.py I checked
- Which billing accounts have more than one app account? 
  (Search this title in explore.py ^^^ )

*/