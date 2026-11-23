UPDATE outbox
SET status = 'parked', attempts = attempts + 1, last_error = %(error)s, updated_at = %(now)s
WHERE outbox_id = %(outbox_id)s
