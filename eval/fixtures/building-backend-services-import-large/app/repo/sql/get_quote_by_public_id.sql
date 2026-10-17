SELECT
    quote_id, public_id, garage_id, tariff_id, window_start, window_end,
    amount_cents, currency, breakdown, expires_at, created_at
FROM quote
WHERE public_id = %(public_id)s;
