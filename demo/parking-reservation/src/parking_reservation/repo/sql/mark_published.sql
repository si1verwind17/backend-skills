UPDATE outbox
SET status = 'published', published_at = %(now)s, last_error = NULL, updated_at = %(now)s
WHERE outbox_id = %(outbox_id)s
