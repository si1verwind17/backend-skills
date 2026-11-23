UPDATE outbox
SET attempts = attempts + 1, last_error = %(error)s,
    next_attempt_at = %(next_attempt_at)s, updated_at = %(now)s
WHERE outbox_id = %(outbox_id)s
