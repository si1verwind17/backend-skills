-- The row stays due and is retried on the next dispatch run until it
-- reaches the attempt limit in claim_due_notifications.
UPDATE notification_outbox
SET attempt_count = attempt_count + 1, last_error = %(error)s, updated_at = %(now)s
WHERE notification_id = %(notification_id)s;
