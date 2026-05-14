select
    date,
    billing_account_id,
    starting_arr,
    ending_arr,
    ending_arr - starting_arr as arr_change

from 'data/arr_daily.csv'

where 1=1
    and billing_account_id is not null
    and date is not null