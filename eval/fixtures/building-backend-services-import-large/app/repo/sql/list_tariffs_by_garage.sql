SELECT
    tariff_id, garage_id, name, currency, block_minutes, grace_minutes,
    daily_cap_cents, rounding_cents, valid_from, valid_to
FROM tariff
WHERE garage_id = %(garage_id)s
ORDER BY valid_from DESC;
