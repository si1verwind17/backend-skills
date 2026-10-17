-- Settled charges for every garage of one operator, grouped by garage,
-- the garage-local date the charged stay started on, and currency.
SELECT
    c.garage_id,
    (c.charged_from AT TIME ZONE g.timezone)::date AS local_date,
    c.currency,
    count(*) AS charges,
    sum(c.amount_cents)::bigint AS amount_cents
FROM reservation_charge c
JOIN garage g ON g.garage_id = c.garage_id
WHERE g.operator_id = %(operator_id)s
  AND (c.charged_from AT TIME ZONE g.timezone)::date BETWEEN %(first)s AND %(last)s
GROUP BY c.garage_id, local_date, c.currency
ORDER BY c.garage_id, local_date, c.currency;
