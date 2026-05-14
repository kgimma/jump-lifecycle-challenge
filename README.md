# jump-lifecycle-challenge

Gemini helped design the page layout for this and the docs pages. The words and concepts are mine though. 

## Interpretation of the Business Problem

Jump needs to handle the data orchestration from raw product and billing data to trusted lifecycle signals that different teams can act on. There are three core questions:
- Which accounts are healthy? 
- Which are at risk?
- What should we do about it?

The first challenge is what it means for an account to even be healthy. CS wants to know who to call for support. GTM wants to know who to pitch to. Product wants to know which features are driving retention, stagnation, and churn. Leadership wants a number they can monitor and understand. I tried to build one mart that answers an initial question for all stakeholders involved. 

=================================================

## Clarification Questions

1. **How does Jump currently define adoption internally?** Is there an existing definition that CS or Product uses, even informally? I made my best guess, but creating a shared language will help onboarding and eventual projects go smoother. 

2. **What is the typical sales path for expansion?** Does GTM proactively reach out, or do customers self-serve upgrades? I'm sure there's some combination. But the way I'd define flagging would depend on how the different pathways are developed. In my experience, these tend to morph a lot so this would be a continuous conversation. 

3. **Are there known data quality issues with the ARR or usage data?** We found accounts with usage after ARR hits zero. Ss this expected behavior (like when you cancel a streaming service) or would I flag this as a data pipeline issue?

4. **How are seat tiers used in practice?** The app_users table has a seat_tiers_array field. How are they developed? What's their connection to pricing? 

5. **What is the expected lifecycle of a new account?** How long does onboarding typically take? This affects how we define the "new account" exclusions. I used 30 days. Also is there ever successful churn? Like anyone that's had active users for over 6 months is considered a success story?

6. **Is there a hierarchy above billing accounts that matters for CS?** Some billing accounts map to multiple app accounts. Does CS manage at the billing account level or the app account level in real life?

7. **Which product features does the team consider most strategic?** Meetings showed the strongest retention signal in the data, but is this the goal? Or are there other things we'd prefer to see?

8. **What does contraction typically look like operationally?** Is it seat reduction, plan downgrade, or something else? Understanding the mechanism helps interpret the contraction signal. I guessed and defined it as any month where ending_arr < starting_arr, regardless of the cause.

9. **What is the current reporting cadence for CS and Leadership?** Monthly snapshots work for the mart design I built, but I'm curious about what actually exists so far.

=================================================

## Assumptions

- Internal accounts and users are excluded from all models using the `is_internal_account` and `is_internal_user` flags in the source data
- The billing account is the unit of analysis
- Active user = any user with at least one product interaction in a given month across any feature
- The first 30 days after signup are excluded from lifecycle segmentation as accounts may still be onboarding
- For accounts with multiple app accounts, active user rate is averaged across all app accounts mapped to the billing account
- Post-churn usage exists in the data and is excluded from retention analysis queries. It seems like its own question that should get its own analysis.
- Churn is defined as ending_arr = 0 when starting_arr > 0. For accounts that churned more than once, we use the first churn month
- Expansion-ready requires no expansion event in the prior 3 months to avoid re-flagging accounts that just expanded

=================================================

## How to Run

**Requirements:** Python 3.9+, DuckDB, pandas

**Install dependencies:**
```bash
pip3 install duckdb pandas
```

**Place source CSVs in the data/ folder:**
data/
app_accounts.csv
app_users.csv
app_usage_daily.csv
arr_daily.csv
billing_accounts.csv

**Register all models as views:**
```bash
python3 run.py
```

**Run outputs and analysis:**
```bash
python3 final.py
```

**Explore data and validation checks:**
```bash
python3 scratch/explore.py
```

**Note:** In a production environment, the CSV file paths in staging models would be replaced with `{{ ref('model_name') }}` references and deployed to BigQuery via dbt. The run.py or final.py scripts simulate dbt's dependency resolution for this challenge.

=================================================

## Model Design Overview

The project follows dbt-style layered modeling:
Sources (5 CSVs)
↓
Staging (1:1 with sources, light cleaning, internal account exclusion)
↓
Intermediate (joins, monthly aggregations, business logic)
↓
Mart (final reporting table with lifecycle segments, reason codes, recommended actions)
↓
Final.py (this would be the report-level queries that would feed into a BI tool. )
**Staging models:** one per source CSV. Handle null filtering, internal account/user exclusion, and column selection.

**Intermediate models:**
- `int_account_bridge` — maps billing accounts to app accounts using bridge key
- `int_arr_monthly` — aggregates daily ARR to monthly, buckets movement type
- `int_usage_monthly` — aggregates daily usage events to monthly totals / app account
- `int_user_adoption_monthly` — calculates active user rate and days-level feature signals per app account per month

**Mart:** `mart_account_lifecycle_monthly` joins all intermediate models and assigns lifecycle segments, expansion-ready flags, reason codes, and recommended actions.

Full model documentation including grain, join logic, and data quality risks is in `docs/model_design.md`.
Metric and segment definitions are in `docs/metric_definitions.md`.

=================================================

## AI Usage Disclosure

I used Claude and Gemini throughout this project. Claude was more for coding type review and Gemini was more for page design. I tried to write in each section how I used AI, but here's a high level overview. 

**What I used it for:**
- Setting up the project environment and folder structure
- Debugging SQL models -- I'm less used to duckdb so I needed some syntax help
- Writing the Python runner script (setting up to duckdb environment for run.py and final.py and explore.py)
- Drafting documentation (README, metric definitions, model design) gave the page structure and titles and then I filled out the page based on what I did. 
- Suggesting some of the exploratory queries during data investigation (but not most)

**How I validated correctness:**
- Most of what it helped me with was setting up things to run, so if it ran, it worked. 
- When it helped me with SQL syntax it was helping with a single element, which I traced back to having the number I expected. 

=================================================

## Lessons and Reflections

**What I struggled with most:**
Thinking through adoption patterns was the hardest part. The product has many features and therefore many possible combinations to analyze. There's no single right answer for what "adoption" means. It depends on which features matter most to the business. This is a volitile answer. I decided to pick a clear definition and stick with it rather than trying to cover every possible angle, but it required constant reminding myself that a clear opinionated answer is better than an unfinished, disperse one. 

**What I enjoyed most:**
The leadership monitoring question was my favorite. My favorite part of data analytics is the social dimension. Communication and the exchange of knowledge gives me energy in any setting. Building something that a non-technical executive can open on a Monday morning and immediately understand what's happening in the business is deeply satisfying to me. That's the moment where data stops being numbers and starts being a decision. This is the part of the job that most motivates me. 

**What I would do with more time:**
I would build an interactive scorecard where the end user could adjust weights on different product signals (meetings, AI chat, notes, etc.) to start the conversation about which features are actually moving the needle today versus which should be on the roadmap. The mart is already structured with all the signals in place. The next step is giving business users a way to interrogate those signals themselves rather than waiting for an analyst to answer each question.

**How I would prepare better next time:**
I would spend more time upfront aligning on metric definitions before writing any SQL. In a real job context I would have had those stakeholder conversations first. The clarification questions in this README are the questions I would have asked on day one, and having those answers would have saved meaningful time throughout the execution of the project.

**How I used final.py:**
My initial thought was to keep the reports in final.py so you could follow my logic a bit better. It kind of ended up making this megafile that requires a bit of manual work. So to be able to export the CSVs easier I just made a new export_outputs.py and copied and pasted things over. This took a ton of time and could have been avoided with more thoughtful organization. 


=================================================

## Answering the Questions
---

## Analysis: Answers to the 7 Business Questions

Go into final.py for more specific notes

**Q1: Which accounts appear healthy, under-adopted, at risk, or expansion-ready?**
Answered directly by the `lifecycle_segment` column in the mart. Each account is assigned one of four segments each month using cascading logic: healthy (≥80% active user rate, stable/growing ARR, <2% MoM decline), at-risk (<60% active user rate OR contraction OR declining usage), under-adopted (60-79%), or new (first 30 days). See `outputs/q1_q4_q5_account_lifecycle_signals.csv`.

**Q2: Which product adoption patterns appear associated with retention?**
Active user rate is the strongest differentiator between retained and churned accounts. For Small and Medium segments, retained active accounts consistently outperformed churned accounts across every usage metric. Large accounts are an outlier. Churned large accounts had higher usage than retained ones, suggesting their churn may be some factor other than product dissatisfaction. See `outputs/q2_q3_retention_analysis.csv`.

**Q3: Which product adoption patterns appear before churn or contraction?**
We looked at usage in the 3 months before churn or contraction events. Contracted accounts showed definitive decreases in active user rate before contracting. Nearly 25% of retained accounts have zero activity in the last 3 months. These are paying but not using the product. Not sure if this is a data quality issue or represents something else. See `outputs/q2_q3_retention_analysis.csv`.

**Q4: Which accounts appear expansion-ready?**
Answered by the `is_expansion_ready` flag in the mart. An account is expansion-ready if it has ≥80% active user rate, at least one meeting, has not expanded in the last 3 months, and is not a new account. These would be more thought out definitions if I were working on this with a team. I just used this to show that being expansion ready requires the review of more than one dimension. As of the most recent month there are 587 expansion-ready accounts overall. See `outputs/q1_q4_q5_account_lifecycle_signals.csv`. 

**Q5: Which accounts should Customer Success or GTM prioritize, and why?**
Answered by the `recommended_action` and `reason_code` columns in the mart. CS should prioritize accounts flagged `cs_outreach_no_usage`, `cs_outreach_declining`, and `cs_outreach_contraction`. GTM should focus on accounts flagged `gtm_expansion_outreach`. See `outputs/q1_q4_q5_account_lifecycle_signals.csv`.

**Q6: What should Product learn from usage and adoption patterns?**
Meetings are the single strongest engagement signal. Accounts that use meetings have extremely high active user rates. AI chat is underutilized but highly correlated with engagement when used. Could be an education issue or it could be a mistrust of AI issue. Medium contracted accounts were actually the heaviest users before contracting, which could mean they hit a feature or seat ceiling. Small, Medium, and Large accounts show starkly different patterns and should be treated as separate cohorts. See `outputs/q6_product_insights.csv`.

**Q7: What should Leadership monitor monthly?**
A period-over-period summary covering this month vs last month, this quarter vs last quarter, and this year vs last year. All prorated to the same number of months for fair comparison. Example if we're comparing this year vs last year, we just want to see last year through April, not through December. Tracks total accounts, ending ARR, ARR change, avg active users, total activity, meetings, and lifecycle segment counts by customer segment. See `outputs/q7_leadership_summary.csv`.

All CSV outputs would be going into some sort of a visualization tool to make these easier. So imagine that you're seeing charts, dropdowns, and interactivity. 