UPDATE notification_outbox
SET skipped_at = %(now)s, skip_reason = %(reason)s, updated_at = %(now)s
WHERE notification_id = %(notification_id)s;
