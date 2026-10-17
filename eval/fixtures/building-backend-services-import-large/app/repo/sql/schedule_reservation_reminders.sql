-- One reminder per reservation that is still 'reserved' and starts inside
-- the scheduling range. send_after is `lead` before the start, but never
-- in the past, so a late booking is reminded on the next dispatch run.
-- ON CONFLICT makes repeated scheduling runs harmless.
INSERT INTO notification_outbox (
    reservation_id, driver_id, kind, send_after, created_at, updated_at
)
SELECT
    r.reservation_id,
    r.driver_id,
    'reservation_reminder',
    greatest(r.window_start - %(lead)s::interval, %(now)s),
    %(now)s,
    %(now)s
FROM reservation r
WHERE r.status = 'reserved'
  AND r.window_start > %(range_start)s
  AND r.window_start <= %(range_end)s
ON CONFLICT (reservation_id, kind) DO NOTHING
RETURNING notification_id;
