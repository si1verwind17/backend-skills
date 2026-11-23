SELECT outbox_id, event_id, event_type, payload, attempts
FROM outbox
WHERE status = 'pending' AND next_attempt_at <= %(now)s
ORDER BY next_attempt_at, outbox_id
LIMIT 1
FOR UPDATE SKIP LOCKED
