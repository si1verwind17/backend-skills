-- excl_tariff_garage_validity rejects a tariff whose validity overlaps
-- another tariff of the same garage; the repo reports that as
-- OverlappingTariff.
INSERT INTO tariff (
    garage_id, name, currency, block_minutes, grace_minutes, daily_cap_cents,
    rounding_cents, valid_from, valid_to, created_at
)
VALUES (
    %(garage_id)s, %(name)s, %(currency)s, %(block_minutes)s, %(grace_minutes)s,
    %(daily_cap_cents)s, %(rounding_cents)s, %(valid_from)s, %(valid_to)s, %(now)s
)
RETURNING
    tariff_id, garage_id, name, currency, block_minutes, grace_minutes,
    daily_cap_cents, rounding_cents, valid_from, valid_to;
