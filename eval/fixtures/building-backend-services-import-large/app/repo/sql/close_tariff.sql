-- Ends an open-ended tariff so a successor can start on valid_to. Only
-- moves the end earlier; a tariff that already ends sooner is untouched.
UPDATE tariff
SET valid_to = %(valid_to)s
WHERE tariff_id = %(tariff_id)s
  AND valid_from < %(valid_to)s
  AND (valid_to IS NULL OR valid_to > %(valid_to)s)
RETURNING
    tariff_id, garage_id, name, currency, block_minutes, grace_minutes,
    daily_cap_cents, rounding_cents, valid_from, valid_to;
