SELECT
    c.charge_id, c.reservation_id, c.garage_id, c.tariff_id, c.charged_from,
    c.charged_until, c.amount_cents, c.currency, c.settled_at
FROM reservation_charge c
JOIN reservation r ON r.reservation_id = c.reservation_id
WHERE r.public_id = %(public_id)s;
