SELECT
    tariff_id, garage_id, name, currency, block_minutes, grace_minutes,
    daily_cap_cents, rounding_cents, valid_from, valid_to
FROM tariff
WHERE tariff_id = %(tariff_id)s;
