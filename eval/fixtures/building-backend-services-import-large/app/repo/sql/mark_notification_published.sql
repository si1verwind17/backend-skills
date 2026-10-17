UPDATE notification_outbox
SET published_at = %(now)s, attempt_count = attempt_count + 1, updated_at = %(now)s
WHERE notification_id = %(notification_id)s;
