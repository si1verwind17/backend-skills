UPDATE billing_outbox
SET published_at = %(now)s, updated_at = %(now)s
WHERE outbox_id = %(outbox_id)s;
