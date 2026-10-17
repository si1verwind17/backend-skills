INSERT INTO reservation_charge (
    reservation_id, garage_id, tariff_id, charged_from, charged_until,
    amount_cents, currency, settled_at
)
VALUES (
    %(reservation_id)s, %(garage_id)s, %(tariff_id)s, %(charged_from)s, %(charged_until)s,
    %(amount_cents)s, %(currency)s, %(now)s
)
ON CONFLICT (reservation_id) DO NOTHING
RETURNING charge_id;
