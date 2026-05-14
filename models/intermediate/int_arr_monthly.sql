-- Grain: one row per billing_account_id per snapshot_month.
-- starting ARR, ending ARR, and movement type.

-- int_arr_monthly.sql
-- Grain: one row per billing_account_id per snapshot_month.

select
    billing_account_id,
    date_trunc('month', date) as snapshot_month,
    first(starting_arr order by date) as starting_arr,
    last(ending_arr order by date) as ending_arr,
    last(ending_arr order by date) - first(starting_arr order by date) as arr_change,
    case
        when last(ending_arr order by date) = 0 and first(starting_arr order by date) > 0 then 'churned'
        when last(ending_arr order by date) > first(starting_arr order by date) then 'expansion'
        when last(ending_arr order by date) < first(starting_arr order by date) then 'contraction'
        when last(ending_arr order by date) = first(starting_arr order by date) then 'stable'
        else 'unknown'
    end as arr_movement_type

from stg_arr_daily

where 1=1
    and billing_account_id is not null
    and date is not null

group by 1, 2

/*
Notes
- Did anyone have more than one movement type in the same month? (search in scratch.py)
    - No
- Monthly breakdown of movement (search in scratch.py)
    - I found an error here that originally I calculated wrong so it was never counting churn or contraction
    - changed from min(starting_arr) --> first()
                   max(ending_arr) --> last()
*/