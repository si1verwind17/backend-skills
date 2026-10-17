-- Due, unsent notifications with the current reservation and driver
-- state, so the dispatcher can skip ones that no longer apply. The
-- driver join is LEFT: reservations can predate the driver's account.
SELECT
    n.notification_id, n.kind, n.reservation_id, n.driver_id, n.send_after, n.attempt_count,
    r.public_id AS reservation_public_id, r.status AS reservation_status, r.garage_id,
    r.window_start, r.window_end,
    g.name AS garage_name,
    d.email, d.phone, d.notify_reminders
FROM notification_outbox n
JOIN reservation r ON r.reservation_id = n.reservation_id
JOIN garage g ON g.garage_id = r.garage_id
LEFT JOIN driver d ON d.driver_id = n.driver_id
WHERE n.published_at IS NULL
  AND n.skipped_at IS NULL
  AND n.send_after <= %(now)s
  AND n.attempt_count < %(max_attempts)s
ORDER BY n.send_after
LIMIT %(limit)s
FOR UPDATE OF n SKIP LOCKED;
