import duckdb

conn = duckdb.connect()

models = [
    ("stg_billing_accounts", "models/staging/stg_billing_accounts.sql"),
    ("stg_app_accounts",     "models/staging/stg_app_accounts.sql"),
    ("stg_app_users",        "models/staging/stg_app_users.sql"),
    ("stg_usage_daily",      "models/staging/stg_usage_daily.sql"),
    ("stg_arr_daily",        "models/staging/stg_arr_daily.sql"),
]

for name, path in models:
    sql = open(path).read()
    result = conn.execute(sql).df()
    print(f"{name}: {len(result)} rows")