select
    billing_account_id,
    billing_account_name,
    billing_account_bridge_id,
    customer_segment,
    created_date

from 'data/billing_accounts.csv'

where 1=1
    and billing_account_id is not null