INSERT INTO quote (
    public_id, garage_id, tariff_id, window_start, window_end,
    amount_cents, currency, breakdown, expires_at, created_at
)
VALUES (
    %(public_id)s, %(garage_id)s, %(tariff_id)s, %(window_start)s, %(window_end)s,
    %(amount_cents)s, %(currency)s, %(breakdown)s, %(expires_at)s, %(now)s
)
RETURNING quote_id, created_at;
