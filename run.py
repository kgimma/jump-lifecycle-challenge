import duckdb
import os
import re

conn = duckdb.connect()

# ── staging ───────────────────────────────────────────────────
staging_models = [
    'stg_billing_accounts',
    'stg_app_accounts',
    'stg_app_users',
    'stg_usage_daily',
    'stg_arr_daily',
]

# ── intermediate ──────────────────────────────────────────────
intermediate_models = [
    'int_account_bridge',
    'int_arr_monthly',
    'int_usage_monthly',
    'int_user_adoption_monthly',
]

# ── marts ─────────────────────────────────────────────────────
mart_models = [
    'mart_account_lifecycle_monthly',
]

def register_view(folder, name):
    path = f'models/{folder}/{name}.sql'
    sql = open(path).read()
    # strip block comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    conn.execute(f"create or replace view {name} as ({sql})")
    print(f"registered: {name}")

# run in order
for model in staging_models:
    register_view('staging', model)

for model in intermediate_models:
    register_view('intermediate', model)

for model in mart_models:
    register_view('marts', model)

