-- The tariff in force for a garage on a garage-local date. At most one
-- row can match (excl_tariff_garage_validity).
SELECT
    tariff_id, garage_id, name, currency, block_minutes, grace_minutes,
    daily_cap_cents, rounding_cents, valid_from, valid_to
FROM tariff
WHERE garage_id = %(garage_id)s
  AND valid_from <= %(on_date)s
  AND (valid_to IS NULL OR valid_to > %(on_date)s);
