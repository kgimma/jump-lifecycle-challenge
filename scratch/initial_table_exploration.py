import duckdb

conn = duckdb.connect()

# ── billing_accounts ──────────────────────────────────────────
print("\n=== BILLING ACCOUNTS ===")
print(conn.execute("""
    SELECT customer_segment, COUNT(*) as count
    FROM 'data/billing_accounts.csv'
    GROUP BY 1
    ORDER BY 2 DESC
""").df())

# ── app_accounts ──────────────────────────────────────────────
print("\n=== APP ACCOUNTS: internal vs external ===")
print(conn.execute("""
    SELECT is_internal_account, COUNT(*) as count
    FROM 'data/app_accounts.csv'
    GROUP BY 1
""").df())

# ── app_users ─────────────────────────────────────────────────
print("\n=== APP USERS: seat tiers ===")
print(conn.execute("""
    SELECT seat_tiers_array, COUNT(*) as count
    FROM 'data/app_users.csv'
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 10
""").df())

# ── arr_daily ─────────────────────────────────────────────────
print("\n=== ARR: sample of movements ===")
print(conn.execute("""
    SELECT 
        MIN(date) as earliest,
        MAX(date) as latest,
        COUNT(DISTINCT billing_account_id) as accounts,
        ROUND(AVG(ending_arr), 2) as avg_arr
    FROM 'data/arr_daily.csv'
""").df())

# ── app_usage_daily ───────────────────────────────────────────
print("\n=== USAGE: activity breakdown ===")
print(conn.execute("""
    SELECT
        ROUND(AVG(meeting_count), 2) as avg_meetings,
        ROUND(AVG(page_view_count), 2) as avg_page_views,
        ROUND(AVG(ai_chat_message_submitted_count), 2) as avg_ai_chat,
        ROUND(AVG(note_synced_count), 2) as avg_notes
    FROM 'data/app_usage_daily.csv'
""").df())
