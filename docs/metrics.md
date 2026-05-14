# Metric and Segment Definitions

## Overview
All metrics are defined at the billing account level unless otherwise noted.
Grain for all metrics: one row per billing_account_id per snapshot_month. I also wrote the grain within all the intermediate queries

#Gemini helped me design the layout of this page. I still populated the action content.

====================================
====================================

## Core Metrics

### Active User Rate
- **Definition:** The proportion of a billing account's users who had at least one product interaction in a given month.
- **Grain:** billing_account_id + snapshot_month
- **Formula:** active_users / total_users
- **Time window:** calendar month
- **Filters:** excludes internal users (is_internal_user = false)
- **Notes:** Accounts with zero users will have a null rate. Accounts with multiple app accounts are averaged across all app accounts mapped to the billing account. This is sometimes addressed depending on the calculation in Final.py

### Total Activity
- **Definition:** Sum of all product interactions for any event type for a billing account in a given month.
     e.g. meetings, page views, page visits, notes viewed, AI chat messages, notes synced, dashboards viewed, meeting agendas viewed, and tasks synced.
- **Grain:** billing_account_id + snapshot_month
- **Formula:** sum of all event type counts
- **Time window:** calendar month
- **Filters:** excludes internal users
- **Notes:** All event types are weighted equally. A meeting and a page view both count as 1 activity unit. Weighting is a fun challenge, but out of scope for the time constraints of the activity. I like making interactive charts with weights to help guide conversations around this. 

### Total Meetings
- **Definition:** The total number of meetings by billing account in a given month.
- **Grain:** billing_account_id + snapshot_month
- **Time window:** calendar month
- **Filters:** excludes internal users
- **Notes:** Meetings are the strongest single predictor of account health based on our analysis. Accounts with zero meetings are significantly more likely to churn or contract. That doesn't mean other things are not good indicators, or interesting to talk about. AI, for example, isn't super widely used, but in the accounts it is used in, there's such high adoption.

### ARR Change
- **Definition:** The difference between a billing account's ending ARR and starting ARR for a given month.
- **Grain:** billing_account_id + snapshot_month
- **Formula:** last(ending_arr) - first(starting_arr) within the month
- **Time window:** calendar month
- **Notes:** We use first/last by date rather than min/max to correctly capture churn events that occur mid-month. There's a note within that sql page as well. 

===============================================
===============================================

## Segment Definitions
NOTE: These notes are also repeated throughout the tables and folders. So don't feel like you need to hold this information in your brain. 

### Lifecycle Segment
Assigned to each billing account each month via cascading CASE logic. Segments are mutually exclusive and evaluated in this order:

**New**
- Account is within its first 30 days since app signup or billing creation date
- Excluded from all other segments because the first 30 days is probably filled with exploration of some and weariness from others. It's too volitile.
- NOTE: 30 days may span 2 calendar months. Could simplify to first 1-2 calendar months in a future iteration. But I feel like that's inconsisent in another way. 

**Healthy**
- active_user_rate >= 80% AND
- arr_movement_type in ('stable', 'expansion') AND
- MoM active user rate decline < 2%
- All three conditions must be true!!

**At-risk**
- active_user_rate < 60% OR
- arr_movement_type = 'contraction' OR
- MoM active user rate decline >= 2%
- Any one condition is sufficient

**Under-adopted**
- active_user_rate between 60-79%
- Not flagged as at-risk
- Falls between healthy and at-risk

**Unknown**
- Does not meet any of the above conditions
- Typically accounts with no ARR movement type or missing signals

These aren't really all-encompassing, but I wanted to show my general approach to this sort of thing while not losing too much time on it. 

---

### ARR Movement Type
Classified per billing account per month:

| **Type**        | **Definition** |
| churned     | ending_arr = 0 and starting_arr > 0 |
| expansion.  | ending_arr > starting_arr |
| contraction | ending_arr < starting_arr |
| stable      | ending_arr = starting_arr |

**NOTES:**
- 17 accounts churned more than once (resurrection churn). We use first churn month.
- Accounts with zero ARR may still show usage activity — ARR and usage data come from separate systems and may not be perfectly aligned.
- Post-churn usage exists in the data. Analysis queries exclude post-churn months for churned accounts.
- 25% of stable accounts are stably not using the product but still paying. 

These get addressed in the noted on final.py

---

### Expansion-Ready Flag
- **Definition:** An account that shows high usage intensity and has not recently expanded (last 3 months), suggesting they may be ready for upsell or additional seats.
- **Conditions (all must be true):**
  - is_new_account = 0
  - expanded_last_3_months = 0 
  - total_activity > 0
  - active_user_rate >= 80%           This one I really guessed at. I'm sure there's an internal agreement for where we'd want this to be
  - total_meetings > 0
- **Independence:** Expansion-ready is evaluated independently of lifecycle segment. An at-risk account can still be expansion-ready if usage intensity is high enough.
- **NOTES:** Does not account for customer segment size differences. A future iteration could weight expansion-readiness differently for Small vs Medium vs Large accounts or weight certain parts like meeting utilization vs notes utilization vs AI utilization. 

=============================================
=============================================

### Reason Code
A single string label explaining the primary reason for the lifecycle segment assignment. Used for CS and GTM prioritization.

| Code                  | Meaning |
| new_account           | Account is within first 30 days |
| churned               | ARR dropped to zero |
| recent_contraction    | ARR declined this month |
| zero_active_users     | No users were active this month |
| low_active_user_rate  | Active user rate below 60% |
| usage_declining.      | Active user rate dropped more than 2% MoM |
| healthy_usage_and_arr | High active user rate and stable/growing ARR |
| recently_expanded     | Expansion event in last 3 months |
| stable_moderate_usage | No strong signal in either direction |

=============================================

### Recommended Action
A single string label for CS and GTM teams indicating the suggested next step.

| Action                   | Trigger |
| monitor_activation.      | New account |
| churn_review.            | Account churned |
| cs_outreach_contraction  | ARR contracted this month |
| cs_outreach_no_usage     | Zero active users |
| cs_outreach_low_adoption | Active user rate below 60% |
| cs_outreach_declining    | Usage declining MoM |
| gtm_expansion_outreach   | Account is expansion-ready |
| nurture                  | Healthy account, maintain relationship |
| monitor                  | No strong signal, keep watching |

============================================

## Data Quality Notes

### Accounts without app accounts
- Over 17k billing accounts have no matching app account (bridge key)
- These accounts have ARR data but no usage data
- Included in mart with null app signals. There are notes about addressing where necessary in final.py

### Accounts with multiple app accounts
- Over 200 billing accounts map to more than one app account (up to 8)
- Usage and adoption signals are aggregated across all app accounts for the billing account
- Active user rate is averaged across app accounts

### Zero-usage retained accounts
- About 25% of retained accounts had zero activity in the last 3 months
- These accounts are paying but not using the product
- High churn risk despite being technically retained. There are notes about where this is relevant in final.py

### Post-churn usage
- Some accounts show usage activity after their ARR hits zero
- Maybe due to grace periods or data misalignment between billing and product systems? Or just that it's dummy data?
- Analysis queries exclude post-churn months to avoid inflating churned account usage metrics. There are notes in final.py when this happens